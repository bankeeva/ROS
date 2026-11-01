# ПР08: как снять свой скриншот в RViz

Ниже — команды, которые проверены в контейнере `ros-pr07`. В этом контейнере
RViz нужно запускать **от root**, иначе он не видит `/map`, `/clock` и `/tf`
от нод, запущенных от root. Это проверено: RViz от `ubuntu` показывал пустой
экран, RViz от root сразу видит карту и скан.

## 0. Открыть VNC и убрать заставку

Открой `http://localhost:6080` и, если видишь чёрный экран с логотипами MATE,
подвинь мышь или выполни:

```bash
docker exec -u ubuntu -e DISPLAY=:1 -e XAUTHORITY=/home/ubuntu/.Xauthority \
  ros-pr07 mate-screensaver-command -d
```

## 1. Терминал A: локализация

```bash
docker exec -it ros-pr07 bash
source /opt/ros/lyrical/setup.bash
cd /home/ubuntu
source install/setup.bash
ros2 launch localization_case localization.launch.py \
  params_file:=$PWD/src/localization_case/config/amcl.yaml \
  map:=$PWD/.course-kit/v1/fixtures/pr08/map.yaml
```

Дождись строки `Managed nodes are active`.

## 2. Терминал B: RViz с готовым конфигом

```bash
docker exec -e DISPLAY=:1 -e XAUTHORITY=/home/ubuntu/.Xauthority -it ros-pr07 bash
source /opt/ros/lyrical/setup.bash
source /home/ubuntu/install/setup.bash
rviz2 -d /home/ubuntu/evidence/pr08/pr08.rviz --ros-args -p use_sim_time:=true
```

В конфиге уже заданы:

- `Fixed Frame: map`;
- `Map` с топиком `/map` и `Transient Local`;
- `LaserScan` с топиком `/vehicle/scan` и `Best Effort`;
- вид `TopDownOrtho`, центр `(4, 0)`.

Разверни окно RViz на весь экран двойным щелчком по заголовку. Если карта
слишком мелкая или обрезана, покрути колесо мыши над центральной областью
или поменяй `Scale` в панели `Views` (например, 40–60).

## 3. Терминал C: запись

```bash
docker exec -it ros-pr07 bash
source /opt/ros/lyrical/setup.bash
cd /home/ubuntu
source install/setup.bash
ros2 bag play --start-paused --rate 0.5 fixtures/pr07-sensors-fixed
```

Нажми `Space`, чтобы playback пошёл. Когда `ROS Time` внизу RViz станет
примерно 18–25 с и красный скан ляжет на стены, нажми `Space` ещё раз —
playback встанет на паузе, и можно спокойно снимать.

Если `ROS Time` остаётся `0.00`, значит RViz запущен не от root или не
подхватил `/clock`: закрой его и повтори шаг 2 командой выше.

## 4. Скриншот

Из любого терминала на Mac:

```bash
docker exec -e DISPLAY=:1 -e XAUTHORITY=/home/ubuntu/.Xauthority ros-pr07 \
  bash -lc 'ffmpeg -y -loglevel error -f x11grab -i :1 -frames:v 1 /home/ubuntu/evidence/pr08/rviz.png'
```

Проверь файл:

```bash
ls -lh evidence/pr08/rviz.png
```

## 5. Вставить в отчёт

В `evidence/pr08/tf.md` в разделе «Наложение скана на карту» добавь строку:

```markdown
![RViz: скан на карте](rviz.png)
```

Можно оставить и старую картинку `scan-map.png`, и новый скриншот. Если хочешь
заменить старую, поменяй в этой строке `scan-map.png` на `rviz.png`.

## 6. Остановить всё

В терминале C нажми `Ctrl+C`, в терминале B закрой RViz, в терминале A нажми
`Ctrl+C`. Если остались процессы:

```bash
docker exec ros-pr07 bash -lc 'for p in $(pgrep -f "[r]viz2"); do kill -9 $p; done; for p in $(pgrep -f "[n]av2_amcl/amcl"); do kill -9 $p; done; for p in $(pgrep -f "[n]av2_map_server/map_server"); do kill -9 $p; done; for p in $(pgrep -f "[n]av2_lifecycle_manager/lifecycle_manager"); do kill -9 $p; done; for p in $(pgrep -f "[r]os2 bag play"); do kill -9 $p; done'
```

## Важно

Для скриншота **не запускай** `localization_metrics.py`: он перезапишет
`evidence/pr08/localization.json`. Если всё-таки запустишь, после опыта снова
прогони `validate_localization.py` и обнови числа в `tf.md` и `report.json`.
