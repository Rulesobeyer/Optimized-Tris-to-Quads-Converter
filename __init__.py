import bmesh
import bpy
import os
import site
import subprocess
import sys
import threading
from bpy.types import Operator, AddonPreferences
from bpy.props import BoolProperty

bl_info = {
    "name": "Optimized Tris to Quads Converter",
    "author": "Rulesobeyer (https://github.com/Rulesobeyer/)",
    "version": (1, 3, 0),
    "blender": (5, 0, 0),
    "support": "COMMUNITY",
    "category": "Mesh",
    "description": "Tris to quads by mathematical optimization.",
    "location": "Editmode > Face",
    "warning": "",
    "doc_url": "https://github.com/Rulesobeyer/Tris-Quads-Ex",
}

_install_in_progress = False


def get_modules_path():
    return bpy.utils.user_resource("SCRIPTS", path="modules", create=True)


def ensure_modules_in_path():
    modules_path = get_modules_path()
    if modules_path and modules_path not in sys.path:
        sys.path.insert(0, modules_path)
        site.addsitedir(modules_path)


def is_pulp_available():
    ensure_modules_in_path()
    try:
        import pulp
        return True
    except ImportError:
        return False


def get_pulp_version():
    ensure_modules_in_path()
    try:
        import pulp
        return getattr(pulp, '__version__', 'unknown')
    except ImportError:
        return None


class TRISQUADS_OT_install_pulp(Operator):
    bl_idname = "trisquads.install_pulp"
    bl_label = "Install PuLP"
    bl_description = "Install the PuLP linear programming library required for optimization"

    @classmethod
    def poll(cls, context):
        global _install_in_progress
        return not _install_in_progress

    def execute(self, context):
        global _install_in_progress

        if is_pulp_available():
            self.report({'INFO'}, f"PuLP is already installed (version {get_pulp_version()})")
            return {'FINISHED'}

        _install_in_progress = True
        self.report({'INFO'}, "Installing PuLP... Please wait.")

        thread = threading.Thread(target=self._install_pulp_thread)
        thread.daemon = True
        thread.start()

        # Register a timer to check completion
        bpy.app.timers.register(self._check_install_complete, first_interval=1.0)

        return {'FINISHED'}

    def _install_pulp_thread(self):
        global _install_in_progress
        try:
            modules_path = get_modules_path()
            python_exe = sys.executable

            subprocess.run(
                [python_exe, "-m", "ensurepip", "--upgrade"],
                capture_output=True,
                check=False
            )

            result = subprocess.run(
                [
                    python_exe, "-m", "pip", "install",
                    "--target", modules_path,
                    "--upgrade",
                    "--no-user",  # Don't use user site-packages
                    "pulp"
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"PuLP installation error: {result.stderr}")
            else:
                print(f"PuLP installed successfully to {modules_path}")
                ensure_modules_in_path()

        except Exception as e:
            print(f"PuLP installation failed: {e}")
        finally:
            _install_in_progress = False

    @staticmethod
    def _check_install_complete():
        global _install_in_progress

        if _install_in_progress:
            return 1.0 

        ensure_modules_in_path()

        if is_pulp_available():
            print(f"PuLP installation verified (version {get_pulp_version()})")
        else:
            print("PuLP installation could not be verified. You may need to restart Blender.")

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        return None 


class TRISQUADS_OT_uninstall_pulp(Operator):
    bl_idname = "trisquads.uninstall_pulp"
    bl_label = "Uninstall PuLP"
    bl_description = "Remove the PuLP library"

    @classmethod
    def poll(cls, context):
        global _install_in_progress
        return not _install_in_progress and is_pulp_available()

    def execute(self, context):
        try:
            modules_path = get_modules_path()
            python_exe = sys.executable

            result = subprocess.run(
                [
                    python_exe, "-m", "pip", "uninstall",
                    "-y", "pulp"
                ],
                capture_output=True,
                text=True,
                cwd=modules_path
            )

            subprocess.run(
                [
                    python_exe, "-m", "pip", "uninstall",
                    "-y", "pulp",
                    "--target", modules_path
                ],
                capture_output=True,
                text=True
            )

            self.report({'INFO'}, "PuLP uninstalled. Restart Blender to complete removal.")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to uninstall PuLP: {e}")

        return {'FINISHED'}


class TrisToQuadsPreferences(AddonPreferences):
    bl_idname = __package__ if __package__ else __name__

    def draw(self, context):
        layout = self.layout
        global _install_in_progress

        box = layout.box()
        box.label(text="Dependency: PuLP (Linear Programming Library)", icon='PACKAGE')

        if _install_in_progress:
            row = box.row()
            row.label(text="Installation in progress...", icon='TIME')
            row.enabled = False
        elif is_pulp_available():
            row = box.row()
            row.label(text=f"PuLP is installed (version {get_pulp_version()})", icon='CHECKMARK')
            box.operator("trisquads.uninstall_pulp", text="Uninstall PuLP", icon='TRASH')
        else:
            row = box.row()
            row.label(text="PuLP is NOT installed", icon='ERROR')
            box.operator("trisquads.install_pulp", text="Install PuLP", icon='IMPORT')
            box.label(text="Note: Restart Blender after installation if import fails.", icon='INFO')

        box = layout.box()
        box.label(text="Usage:", icon='HELP')
        box.label(text="1. Select a mesh object with triangulated faces")
        box.label(text="2. Enter Edit Mode and select the triangular faces to convert")
        box.label(text="3. Go to Face menu > Optimized Tris to Quads")


class MESH_OT_tris_convert_to_quads_ex(Operator):

    bl_idname = "mesh.tris_convert_to_quads_ex"
    bl_label = "Optimized Tris to Quads"
    bl_description = "Tris to quads by mathematical optimization (ILP)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'MESH'
            and context.active_object.mode == 'EDIT'
        )

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if len(selected_objects) == 0:
            self.report({"WARNING"}, "Select at least one mesh object.")
            return {"CANCELLED"}

        ensure_modules_in_path()
        try:
            from pulp import PULP_CBC_CMD, LpMaximize, LpProblem, LpVariable, lpSum, value
        except ImportError:
            self.report({"ERROR"}, "PuLP is not installed. Enable it in addon preferences.")
            return {"CANCELLED"}

        try:
            # Store the current mode and active object
            original_mode = context.mode
            original_active = context.active_object

            # Process each selected object
            processed_count = 0
            for obj in selected_objects:
                # Ensure we're in object mode to change active object
                if context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode="OBJECT")

                # Set this object as active
                context.view_layer.objects.active = obj

                # Convert tris to quads for this object (handles mode switching internally)
                self.convert_tris_to_quads(context)
                processed_count += 1

            # Restore original mode and active object
            if original_active:
                try:
                    # Check if object still exists by trying to access its name
                    _ = original_active.name
                    if original_active.name in bpy.data.objects:
                        context.view_layer.objects.active = original_active
                        if original_mode == 'EDIT_MESH' and original_active.type == 'MESH':
                            bpy.ops.object.mode_set(mode="EDIT")
                        else:
                            bpy.ops.object.mode_set(mode="OBJECT")
                except (ReferenceError, AttributeError):
                    # Object was deleted, just restore mode if possible
                    if original_mode == 'EDIT_MESH':
                        bpy.ops.object.mode_set(mode="OBJECT")

        except Exception as e:
            self.report({"ERROR"}, f"Conversion failed: {e}")
            return {"CANCELLED"}

        if processed_count > 1:
            self.report({"INFO"}, f"Processed {processed_count} objects.")

        return {"FINISHED"}

    def convert_tris_to_quads(self, context):
        from pulp import PULP_CBC_CMD, LpMaximize, LpProblem, LpVariable, lpSum, value

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.mode_set(mode="EDIT")
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        m = LpProblem(sense=LpMaximize)
        edges = {}
        for edge in bm.edges:
            if not self.is_valid_edge(edge):
                continue
            ln = edge.calc_length()
            edges[edge] = LpVariable(f"v{len(edges):03}", cat="Binary"), ln

        if not edges:
            self.report({"INFO"}, f"{obj.name}: No valid triangle pairs found.")
            bm.free()
            return

        mx = max([i[1] for i in edges.values()], default=1)
        m.setObjective(lpSum(v * (1 + 0.1 * ln / mx) for edge, (v, ln) in edges.items()))
        self.add_constraints(bm, m, edges)
        self.solve_problem(m, edges, obj)

        bm.free()

    def is_valid_edge(self, edge):
        return (
            edge.select
            and len(edge.link_faces) == 2
            and edge.link_faces[0].select
            and edge.link_faces[1].select
            and len(edge.link_faces[0].edges) == 3
            and len(edge.link_faces[1].edges) == 3
        )

    def add_constraints(self, bm, problem, edges):
        from pulp import lpSum

        for face in bm.faces:
            if len(face.edges) != 3:
                continue
            vv = [vln[0] for edge in face.edges if (vln := edges.get(edge)) is not None]
            if len(vv) > 1:
                problem += lpSum(vv) <= 1

    def solve_problem(self, problem, edges, obj):
        from pulp import PULP_CBC_CMD, value

        solver = PULP_CBC_CMD(gapRel=0.01, timeLimit=60, msg=False)
        problem.solve(solver)

        if problem.status != 1:
            self.report({"INFO"}, f"{obj.name}: Optimization did not find a solution.")
        else:
            bpy.ops.mesh.select_all(action="DESELECT")
            n = 0
            for edge, (v, _) in edges.items():
                if value(v) > 0.5:
                    edge.select_set(True)
                    n += 1

            self.report({"INFO"}, f"{obj.name}: {n} edges dissolved.")
            bpy.ops.mesh.dissolve_edges(use_verts=False)
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.mesh.select_face_by_sides(type="NOTEQUAL")
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.mode_set(mode="EDIT")


def menu_func_tris_to_quads(self, context):
    self.layout.operator(MESH_OT_tris_convert_to_quads_ex.bl_idname)


# Registration
classes = (
    TRISQUADS_OT_install_pulp,
    TRISQUADS_OT_uninstall_pulp,
    TrisToQuadsPreferences,
    MESH_OT_tris_convert_to_quads_ex,
)


def register():
    ensure_modules_in_path()

    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_edit_mesh_faces.append(menu_func_tris_to_quads)


def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_faces.remove(menu_func_tris_to_quads)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()