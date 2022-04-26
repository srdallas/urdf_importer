***Additional Steps for Converting URDFs***

1. Blender may not work out of the bat, so you will need to include any dependencies noted in a ModuleNotFoundError
2. For me these were rospkg, pyyaml, and a few others.
3. To fix this error place the dependencies in the site-packages folder of the local python base inside of the linux based blender implementation
