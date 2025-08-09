# Tris to Quads Windows

## Overview

Add a proper command line arguments for Windows Powershell cli to install PulP python external package into Blender working environment. More specifically to tackle missing PulP package issue in Windows operating system when using Tris to Quads addon originally made by [Tsutomu Saito](https://github.com/SaitoTsutomu/Tris-Quads-Ex) later on optimized by [Rulesobeyer](https://github.com/Rulesobeyer/Optimized-Tris-to-Quads-Converter)

*copy this cli args to windows powershell, and change ***YourName*** with your actual user name and change Blender version to the one that you use:*

## Proper PulP Installation
```
& "C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe" -m pip install pulp --target "C:\Users\YourName\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\modules"
```

*additionaly you can check if folder name pulp exists in this specific directory*

```
C:\Users\YourName\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\modules
```
*if installed correctly "PulP is Installed" will shown on ***Rulesobeyer Optimized Tris to Quads Converter*** addons preferences menu.*

this solution is not machine agnostic meaning: 
- it needs to know which Blender version you use
- it needs to know your actual username
- it neds to know whether the preferences directory has been created, which is a specific problem in Windows where this directory is not being created on the newly installed Blender
- it needs to know your actual blender installation directory, this solution assumes, your Blender is located in `C:\Program Files\ Blender Foundation\...`

## Credits

- **Original Author**: Tsutomu Saito (https://github.com/SaitoTsutomu/Tris-Quads-Ex)
- **Improved Version**: Rulesobeyer (https://github.com/Rulesobeyer/)