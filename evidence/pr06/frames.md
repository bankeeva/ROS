# PR06 — дерево фреймов и владельцы публикации

| Joint | Parent | Child | Тип | Ожидаемое преобразование (м) | Владелец публикации |
|---|---|---|---|---|---|
| camera_joint | base_link | camera_link | fixed | xyz=(0.20, 0.0, 0.10), rpy=(0,0,0) | robot_state_publisher → /tf_static |
| lidar_joint  | base_link | lidar_link  | fixed | xyz=(0.0, 0.0, 0.20), rpy=(0,0,0) | robot_state_publisher → /tf_static |
| imu_joint    | base_link | imu_link    | fixed | xyz=(-0.10, 0.0, 0.0), rpy=(0,0,0) | robot_state_publisher → /tf_static |
| front_left_wheel_joint  | base_link | front_left_wheel_link  | continuous | xyz=(0, +0.18, 0), axis=Y | joint_states publisher (вручную) |
| front_right_wheel_joint | base_link | front_right_wheel_link | continuous | xyz=(0, -0.18, 0), axis=Y | joint_states publisher (вручную) |
| rear_left_wheel_joint   | base_link | rear_left_wheel_link   | continuous | xyz=(0, +0.18, 0), axis=Y | joint_states publisher (вручную) |
| rear_right_wheel_joint  | base_link | rear_right_wheel_link  | continuous | xyz=(0, -0.18, 0), axis=Y | joint_states publisher (вручную) |

## Владельцы каналов

- `/tf_static` — единственный издатель: `robot_state_publisher` (fixed joints). Профиль RELIABLE + TRANSIENT_LOCAL.
- `/tf` — `robot_state_publisher` публикует только при наличии `/joint_states` для continuous joints. Профиль RELIABLE + VOLATILE.
- `/joint_states` — в зачётной части никто не публикует; при желании — ручной `ros2 topic pub`.

## Диагностика дефекта

- На ветке `pr06-break-lidar-parent` parent у `lidar_joint` был `camera_link` — тест `test_lidar_parent_is_base_link` падал, `tf2_echo base_link lidar_link` показывал смещение, соответствующее сумме camera+lidar offset.
- После исправления parent обратно на `base_link` тест зелёный, `tf2_echo` показывает ровно `lidar_xyz`.