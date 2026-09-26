# ПР02
## 1
```bash
cd "$(git rev-parse --show-toplevel)"

# Ничего не выводит
```
- ```git rev-parse --show-toplevel``` - команда GIT, которая выводит абсолютный путь к корню репозитория
- ```$()``` - то что вывела команда внутри скобок использовать как аргумент для внешней команды
- ```cd``` - перейти в директорию        

В итоге команда просто переводит в корневую папку проекта   

```bash
mkdir -p src evidence/pr02

# Ничего не выводит
```
- ```mkdir``` - создает директорию
- ```-p``` - флаг, который создает промежуточную директорию, если ее нет, работает даже если целевая директория уже существует  

Команда создает два каталога src и evidence/pr02
```bash
printenv ROS_DISTRO ROS_DOMAIN_ID

# Вывод:
lyrical
7
```
- ```printenv``` - печатает значение переменных окружения, если указать конкретные имена, то выведет только их  
- ```ROS_DISTRO``` - переменная, которая говорит какой дистрибутив у ROS подключен  
- ```ROS_DOMAIN_ID``` - идентификатор, который ROS использует для изоляции обмена сообщениями  
### Дополнительно:
- ```>``` - перенаправляет вывод команды в файл, например - ```colcon build > build.txt```  
- ```|``` - вывод одной комнды передается на вход другой, например ```colcon build 2>&1 | tee build.txt```, работает через потоки, в отличии от ```$()```  
- ```source``` - команда, которая выполняет скрипт в текущем терминале, не создавая дочернего процесса, в отличие от запуска через ```bash``` переменные окружения остаются в текущем терминале, а не исчезают с дочерним процессом  

## 3
```bash
# A терминал
ros2 launch turtle_bringup sim.launch.py
```
```bash
# B терминал
source /opt/ros/lyrical/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=7
ros2 node list --no-daemon --spin-time 2

# Вывод
/turtlesim
```
Остановка в терминале А и повторный запуск
```bash
# A терминал
ros2 launch turtle_bringup sim.launch.py
```
## 4
Начальные данные
```bash
# C
ros2 interface show geometry_msgs/msg/Twist
ros2 topic type /turtle1/pose
ros2 topic echo /turtle1/pose --once

# Вывод:
# This expresses velocity in free space broken into its linear and angular parts.

Vector3  linear
	float64 x
	float64 y
	float64 z
Vector3  angular
	float64 x
	float64 y
	float64 z
turtlesim_msgs/msg/Pose
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
```
```bash
# B
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'

# Вывод
publisher: beginning loop
publishing #1: geometry_msgs.msg.Twist(linear=geometry_msgs.msg.Vector3(x=1.0, y=0.0, z=0.0), angular=geometry_msgs.msg.Vector3(x=0.0, y=0.0, z=0.5))
```
```bash
# C
ros2 topic echo /turtle1/pose --once

# Вывод
# This expresses velocity in free space broken into its linear and angular parts.

Vector3  linear
	float64 x
	float64 y
	float64 z
Vector3  angular
	float64 x
	float64 y
	float64 z
turtlesim_msgs/msg/Pose
x: 6.509308815002441
y: 5.796990871429443
theta: 0.5040000081062317
linear_velocity: 0.0
angular_velocity: 0.0
```
`x` увеличился - движение вперед, `y` тоже изменился, `theta` стал положительным. Черепашка пошла по дуге.
## 5
### Сбой
```bash
# B
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'

# Вывод
publisher: beginning loop
publishing #1: geometry_msgs.msg.Twist(linear=geometry_msgs.msg.Vector3(x=1.0, y=0.0, z=0.0), angular=geometry_msgs.msg.Vector3(x=0.0, y=0.0, z=0.5))
```
Черепашка не двигается.
Проверка топиков
```bash
# В С тем времинем
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose

# Вывод
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: _ros2cli_7065
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: PUBLISHER
GID: 01.0f.eb.7d.99.1b.76.2e.00.00.00.00.00.00.07.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): KEEP_LAST (10)
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 0

Type: geometry_msgs/msg/Twist

Publisher count: 0

Subscription count: 1

Node name: turtlesim
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: SUBSCRIPTION
GID: 01.0f.eb.7d.49.1a.59.d7.00.00.00.00.00.00.1c.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): KEEP_LAST (7)
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite
```
Ключевые строки   
```bash
Publisher count: 1
Node name: _ros2cli_7065
Subscription count: 0
```
у топика 1 издатель, но 0 подписчиков - черепашка этот топик не слушает.  
```bash
Publisher count: 0
Subscription count: 1
Node name: turtlesim
```
черепашка слушает этот топик, но издателя сюда никто не шлет
### Исправление

```bash
# B
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \ \ 
  /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'

# Вывод
publisher: beginning loop
publishing #1: geometry_msgs.msg.Twist(linear=geometry_msgs.msg.Vector3(x=1.0, y=0.0, z=0.0), angular=geometry_msgs.msg.Vector3(x=0.0, y=0.0, z=0.5))
```
Черепашка начала движение
```bash
# C
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose

# Вывод
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: _ros2cli_7121
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: PUBLISHER
GID: 01.0f.eb.7d.d1.1b.86.cb.00.00.00.00.00.00.07.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): KEEP_LAST (10)
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 1

Node name: turtlesim
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: SUBSCRIPTION
GID: 01.0f.eb.7d.49.1a.59.d7.00.00.00.00.00.00.1c.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): KEEP_LAST (7)
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

```
Ключевые строки у /turtle1/cmd_vel
```bash
Publisher count: 1
Node name: _ros2cli_7121
Subscription count: 1
Node name: turtlesim
```
Теперь 1 издатель и 1 подписчик - команда доходит, и черепашка двигается.

### Почему правильного типа сообщения недостаточно
Тип сообщения (`geometry_msgs/msg/Twist`) — это только формат данных. Чтоб команда дошла нужен еще точный адрес - полное имя топика.   

В ROS коммуникация происходит только при совпадении Имени топика и Типа сообщения.

В лабораторной тип сообщения был правильным в обоих случаях, но топик разный.