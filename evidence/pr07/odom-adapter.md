# PR07 — адаптер одометрии и владельцы tf

## Что делает адаптер

`course_simulation/odom_adapter.py` — единственное место, где снимается
префикс модели с одометрии Gazebo. Он подписан на `/vehicle/odom_gz`,
публикует `/vehicle/odom` и единственное динамическое преобразование
`odom -> base_link` в `/tf`.

```
Gazebo /model/course_ackermann/odometry
        │  (ros_gz_bridge, GZ -> ROS)
        ▼
/vehicle/odom_gz   course_ackermann/odom  ->  course_ackermann/base_link
        │  odom_adapter.py
        ▼
/vehicle/odom      odom -> base_link
/tf                odom -> base_link  (тот же stamp, что у сообщения)
```

## Исходные и нормализованные frames

| | topic | header.frame_id | child_frame_id |
|---|---|---|---|
| до адаптера | `/vehicle/odom_gz` | `course_ackermann/odom` | `course_ackermann/base_link` |
| после адаптера | `/vehicle/odom` | `odom` | `base_link` |

Обе исходные строки зафиксированы в `evidence/pr07/sensors.json`
(`odometry.raw.frame_id`, `odometry.raw.child_frame_id`) и в
`evidence/pr07/command-path.txt` (разделы 4 и 5).

## Что сохраняется и что проверяется

Адаптер **не** пересчитывает позу и не меняет время:

* `header.stamp` копируется без изменений;
* `pose` (position, orientation, covariance[36]) копируется целиком;
* `twist` (linear, angular, covariance[36]) копируется целиком;
* меняются только `header.frame_id` и `child_frame_id`.

Сообщение отклоняется (ничего не публикуется, пишется диагностика), если:

* `header.frame_id != "course_ackermann/odom"`;
* `child_frame_id != "course_ackermann/base_link"`;
* любое число в pose, twist или в обеих covariance не конечно (NaN/∞).

Проверки реализованы в `course_simulation/kinematics.py`
(`normalize_odometry`) и покрыты тестами
`test_kinematics.py::test_odometry_frames_are_normalised_and_data_preserved`,
`...::test_odometry_with_unknown_prefix_is_rejected`,
`...::test_odometry_with_non_finite_covariance_is_rejected`,
`...::test_transform_matches_odometry_and_keeps_stamp`.

## Владельцы преобразований

| Ребро | Тип | Владелец | QoS |
|---|---|---|---|
| `odom -> base_link` | dynamic | `odom_adapter.py` (единственный писатель) | RELIABLE, KEEP_LAST(100), VOLATILE |
| `base_link -> camera_link` | static | `robot_state_publisher` | RELIABLE, TRANSIENT_LOCAL |
| `base_link -> lidar_link` | static | `robot_state_publisher` | RELIABLE, TRANSIENT_LOCAL |
| `base_link -> imu_link` | static | `robot_state_publisher` | RELIABLE, TRANSIENT_LOCAL |

`robot_state_publisher` создаёт издателя `/tf`, но без публикатора
`/joint_states` он не пишет динамических преобразований; в записи на 2227
сообщений `/vehicle/odom` приходится 2228 сообщений `/tf`, то есть ровно одно
преобразование на каждый отсчёт одометрии. Статические преобразования приходят
из URDF ПР06 и лежат в `/tf_static` (одно transient-local сообщение в bag).

## Доказательство сохранения метки времени

1. Модульный тест `test_transform_matches_odometry_and_keeps_stamp`:
   `stamp` сообщения (12 s, 345 ns) совпадает у `/vehicle/odom` и у
   `TransformStamped`, а translation/rotation берутся из `pose.pose`.
2. `evidence/pr07/command-path.txt`: `tf2_echo odom base_link` показывает ту же
   позу, что и `/vehicle/odom` (x растёт 2.39 → 3.73 м за 15 с, при команде
   0.15 м/с), `frame_id` в `/vehicle/odom` — `odom`.
3. `evidence/pr07/bag-info.txt`: 2227 сообщений `/vehicle/odom` и 2228 `/tf`
   при 44.577 с симуляционного времени.

## Замечания

* `/vehicle/odom_gz` — исходный топик с префиксом модели; в `bridge.yaml`
  переименован **только** `ros_topic_name` (правило из условия ПР07), топик
  Gazebo остался `/model/course_ackermann/odometry`.
* Мост публикует `/vehicle/odom_gz` с QoS RELIABLE + TRANSIENT_LOCAL
  (KEEP_LAST 1) — это поведение `ros_gz_bridge`; адаптер подписан RELIABLE +
  VOLATILE, совместимость соблюдена.
* В записи ПР07 уже лежит нормализованная одометрия и tf; при replay в ПР08
  адаптер повторно **не** запускается.
* Статические смещения берутся из URDF ПР06 (договор проекта); SDF курса
  задаёт свои смещения сенсоров (0.28, 0, 0.38). ПР07 проверяет связность
  дерева и владельцев, а не метрическое совпадение URDF и SDF.
