# Отчёт по практике PR01: Граф ROS 2 и изоляция доменов

## 1. Команды и вывод

#### Список нод
```bash
ros2 node list --no-daemon --spin-time 2

# Вывод:
/teleop_turtle  
/turtlesim
```

#### Список топиков и их типов
```bash
ros2 topic list -t

# Вывод:
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/rosout [rcl_interfaces/msg/Log]
/turtle1/cmd_vel [geometry_msgs/msg/Twist]
/turtle1/color_sensor [turtlesim_msgs/msg/Color]
/turtle1/pose [turtlesim_msgs/msg/Pose]
```

#### Информация о ноде симулятора
```bash
ros2 node info /turtlesim

# Вывод:
/turtlesim
  Subscribers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /turtle1/cmd_vel: geometry_msgs/msg/Twist
  Publishers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
    /turtle1/color_sensor: turtlesim_msgs/msg/Color
    /turtle1/pose: turtlesim_msgs/msg/Pose
  Service Servers:
    /clear: std_srvs/srv/Empty
    /kill: turtlesim_msgs/srv/Kill
    /reset: std_srvs/srv/Empty
    /spawn: turtlesim_msgs/srv/Spawn
    /turtle1/set_pen: turtlesim_msgs/srv/SetPen
    /turtle1/teleport_absolute: turtlesim_msgs/srv/TeleportAbsolute
    /turtle1/teleport_relative: turtlesim_msgs/srv/TeleportRelative
    /turtlesim/describe_parameters: rcl_interfaces/srv/DescribeParameters
    /turtlesim/get_parameter_types: rcl_interfaces/srv/GetParameterTypes
    /turtlesim/get_parameters: rcl_interfaces/srv/GetParameters
    /turtlesim/get_type_description: type_description_interfaces/srv/GetTypeDescription
    /turtlesim/list_parameters: rcl_interfaces/srv/ListParameters
    /turtlesim/set_parameters: rcl_interfaces/srv/SetParameters
    /turtlesim/set_parameters_atomically: rcl_interfaces/srv/SetParametersAtomically
  Service Clients:

  Action Servers:
    /turtle1/rotate_absolute: turtlesim_msgs/action/RotateAbsolute
  Action Clients:

```
#### Тип сообщения позы
```bash
ros2 topic type /turtle1/pose

# Вывод:
turtlesim_msgs/msg/Pose
```

#### bash-команда, которая сохраняет результат команды в переменную POSE_TYPE.
```bash
POSE_TYPE=$(ros2 topic type /turtle1/pose)
```

#### Вывод позиции черепахи единожды
```bash
ros2 topic echo /turtle1/pose --once

# Вывод:
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
```

#### Частота публикации
```bash
ros2 topic hz /turtle1/pose

# Вывод за 12 сек:
average rate: 62.477
	min: 0.009s max: 0.023s std dev: 0.00226s window: 61
average rate: 62.453
	min: 0.009s max: 0.023s std dev: 0.00222s window: 124
average rate: 62.487
	min: 0.009s max: 0.023s std dev: 0.00199s window: 186
average rate: 62.495
	min: 0.009s max: 0.023s std dev: 0.00196s window: 249
average rate: 61.435
	min: 0.001s max: 0.108s std dev: 0.00567s window: 306
average rate: 61.596
	min: 0.001s max: 0.108s std dev: 0.00525s window: 369
average rate: 61.746
	min: 0.001s max: 0.108s std dev: 0.00497s window: 431
average rate: 61.817
	min: 0.001s max: 0.108s std dev: 0.00467s window: 494
average rate: 61.915
	min: 0.001s max: 0.108s std dev: 0.00443s window: 557
average rate: 61.971
	min: 0.001s max: 0.108s std dev: 0.00425s window: 619
average rate: 62.011
	min: 0.001s max: 0.108s std dev: 0.00409s window: 682

# Среднее: 62.0 Hz; min: 0.001s; max: 0.108s
```

## 2. Ноды и их роли
* /turtlesim: нода-симулятор. Отрисовывает окно с черепахой, публикует её текущие координаты и ориентацию в топик /turtle1/pose, и слушает команды скорости в топике /turtle1/cmd_vel.
* /teleop_turtle: нода управления. Считывает нажатия клавиш со стрелками из терминала и публикует сообщения типа geometry_msgs/msg/Twist в топик /turtle1/cmd_vel.

## 3. До/Сбой/После

| Состояние | Домен симулятора | Домен teleop | Видимые ноды | Видимые позы | Код возврата |
| ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
| До | 0  | 0 | /turtlesim, /teleop_turtle | Приходит  | 0 |
| Сбой | 0  | 17 | /teleop_turtle | Не риходит  | 124 |
| После | 0  | 0 | /turtlesim, /teleop_turtle | Приходит  | 0 |

### ломаем
```bash
export ROS_DOMAIN_ID=17
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-broken.txt 2>&1
printf 'exit=%s\n' "$?"

# вывод:
/teleop_turtle
exit=124
```
### чиним
```bash
export ROS_DOMAIN_ID=0
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-fixed.txt 2>&1
printf 'exit=%s\n' "$?"

#вывод:
/teleop_turtle
/turtlesim
exit=0
```
## 4. Объяснение поведения
Для сбоя мы поменяли домен в треминале В.  
Программа считывает ```ROS_DOMAIN_ID``` только при запуске, тоесть симулятор все время работал на домене 0, поэтому достаточно было перезапустить ```teleop``` с доменом 0, чтоб они снова были в одной сети.