# ПР04 — Параметры движения

## Команды и вывод

### Изменение частоты на допустимое значение (10 → 5 Гц)
```bash
ros2 param set /patrol publish_hz 5.0
Set parameter successful
```

### Попытка установить 0 (отклонена)
```bash
ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz must be in [1, 30]
```

### Отрицательное значение (отклонено)
```bash
ros2 param set /patrol publish_hz -5.0
Setting parameter failed: publish_hz must be in [1, 30]
```

### Превышение верхней границы (отклонено)
```bash
ros2 param set /patrol publish_hz 50.0
Setting parameter failed: publish_hz must be in [1, 30]
```

### Проверка реальной частоты потока после изменения
```bash
ros2 topic hz /turtle1/cmd_vel
average rate: 4.972
    min: 0.199s max: 0.203s std dev: 0.00147s window: 4
average rate: 4.994
    min: 0.195s max: 0.203s std dev: 0.00281s window: 9
average rate: 4.995
    min: 0.195s max: 0.203s std dev: 0.00246s window: 14
average rate: 4.993
    min: 0.195s max: 0.206s std dev: 0.00294s window: 19
average rate: 4.999
    min: 0.195s max: 0.206s std dev: 0.00296s window: 24
```

Вывод подтверждает: после установки `publish_hz=5.0` частота публикаций на `/turtle1/cmd_vel` стала ≈ 5 Гц. Старый таймер остановлен, новый работает с периодом 1/5 = 0.2 с.

## Вызов готового сервиса /clear
```bash
ros2 service call /clear std_srvs/srv/Empty
requester: making request: std_srvs.srv.Empty_Request()

response:
std_srvs.srv.Empty_Response()
```

Сервис `/clear` возвращает черепашку в начальное состояние (центр окна, угол 0).

## Список готовых действий
```bash
ros2 action list -t
/turtle1/rotate_absolute [turtlesim_msgs/action/RotateAbsolute]
```

## Отличие запроса (Service) от цели (Action)

**Service (запрос)** — это синхронный вызов по принципу «запрос → ответ»: клиент отправляет запрос и ждёт финальный результат, не имея возможности наблюдать промежуточный прогресс или отменить выполнение.

**Action (цель)** — это асинхронная длительная задача: клиент получает промежуточный **feedback** (обратную связь) в процессе выполнения и может в любой момент отправить **cancel** для отмены цели, а по завершении получает итоговый **result**.