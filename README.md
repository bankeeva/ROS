# ROS
### Запуск
```bash
# Все терминалы
source /opt/ros/lyrical/setup.bash
export ROS_DOMAIN_ID=(какой нужен)

# Терминал А - отображение черепашки
ros2 run turtlesim turtlesim_node

# Терминал В - управление
ros2 run turtlesim turtle_teleop_key
```
