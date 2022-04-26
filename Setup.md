Step 1: Microsoft store and download/install ubuntu 20.04

Step 2: http://wiki.ros.org/noetic/Installation/Ubuntu

Step 2.1: When you go to install, there may be an issue with the key at step 1.4. Follow this link to fix it:
https://answers.ros.org/question/325039/apt-update-fails-cannot-install-pkgs-key-not-working/

```sudo apt-key del 421C365BD9FF1F717815A3895523BAEEB01FA116```

```sudo -E apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654 ```

Step 3.
```source /opt/ros/noetic/setup.bash```

add the above code to your bash.rc file

***NOTE:*** If you have visual studio code installed you can type code .bashrc from the linux terminal and it will open it for you to edit files, this can be used as a text editor 

***Potential Error:*** ( Errno 13 Permission Denied) ***FIX:*** Type id in the ros directory and check the user and group names
```cmd: sudo chown -R username:groupname . ``` (replace user and group with the names you found with id)

***Potential Error:*** (No CMAKE_CXX_COMPILER could be found.) ***FIX:*** ```sudo apt-get install build-essential```

This will install the g++ compiler

***Now, that your WSL is setup:***

1. In Unreal machine, download/Clone latest ROSIntegration from [github][https://github.com/code-iai/ROSIntegration]
2. Move ROSIntegration into the Plugins folder in your Unreal project
3. Rebuild and run project
4. Go to Edit -> Plugins, activate ROSIntegration, and restart project
5. In ROS machine, create a ROS workspace
6. Install ROS Bridge v0.11.10:
```bash
cd ~/my_ros_workspace/src
git clone -b 0.11.10 git@github.com:RobotWebTools/rosbridge_suite.git
or
git clone -b 0.11.10 https://github.com/RobotWebTools/rosbridge_suite.git
```
Error: 'fatal: Could not read from remote repository.'

    Do: ```ssh-add ~/.ssh/id_rsa```
    
    Error: 'Could not open a connection to your authentication agent.'
    
    Do: ```eval `ssh-agent -s` ```

Apply [this commit][https://github.com/RobotWebTools/rosbridge_suite/pull/545/files] to the respective ROS Bridge files
build workspace:
```bash
cd ~/my_ros_workspace
catkin_make
source ./devel/setup.sh
```
Run ROS Bridge in `bson` mode:
```bash
roslaunch rosbridge_server rosbridge_tcp.launch bson_only_mode:=True
```
***NOTE:*** You might get errors when building/running ROS Bridge due missing packages, this normal. Errors should display the name of the missing packages. Install them with `sudo apt install ros-<ros version name>-<package name>`.

***Potential Error:*** (Missing rosauth) ***FIX:*** ``` sudo apt install ros-noetic-rosauth  ```

***NOTE:*** You may also get missing packages that are not within the ```ros-noetic-<package name> ```

***Potential Error:*** (Missing tornado) ***FIX:*** ``` sudo apt install python3-pip && sudo python3 -m pip install tornado ```

***Potential Error:*** (Missing bson) ***FIX:*** ``` sudo python3 -m pip install pymongo ```

Get ROS machine IP address:
```bash
ip address
```
Back in Unreal machine, create a new C++ or Blueprint class of type `ROSIntegrationGameInstance`.
Depending on class created:

If Blueprint, open it up and, in the class defaults, change `ROSBridgeServerHost` to the ROS machine's IP address and `ROSBridgeServerPort` to 9090 (this is the default port, can be changes in the launch file parameters)

If C++, add these lines to the `.cpp` file of the class and recompile:
```cpp
	ROSBridgeServerHost = "172.17.219.40";
    ROSBridgeServerPort = 9090;
```
code-iai/ROSIntegration
Stars
272
Language
C++
Added by GitHub
