# Эксплуатация демо

Приложение CPU и HTTPS tunnel работают как `systemd --user` units `cashguard.service` и `cashguard-tunnel.service`. В действующем развёртывании оба enabled/active; `Linger=yes`, поэтому logout SSH не останавливает менеджер сервисов. Это не гарантирует доступность GPU хоста, электричества, сети или аккаунта ngrok.

```bash
systemctl --user status cashguard.service cashguard-tunnel.service
systemctl --user restart cashguard.service
curl -f http://127.0.0.1:9017/healthz
journalctl --user -u cashguard.service --since '10 minutes ago'
```

Не перезапускайте приложение во время активной проверки: `/healthz` содержит `busy`. После рестарта незавершённые задания становятся `failed`, не отрицательными результатами. SQLite и runtime сохраняются; оригинал MOV удаляется после окончания. При аварийном завершении временные кадры очищаются при следующем запуске.

## Повторить CPU deployment

Создайте `~/cashguard` и установите зависимости в его `.venv`, FFmpeg и ngrok из официальных источников. `deploy/systemd/` содержит шаблоны units. Подставьте свой путь к бинарнику ngrok, если он не находится в `/usr/local/bin` или `/usr/bin`. Скопируйте конфигурацию приложения в `~/cashguard/private/service.env`, отдельные ключи — в файлы с mode 0600; каталог private — 0700. Переменная `NGROK_URL=https://ваш-домен.ngrok-free.dev` задаётся в `private/tunnel.env`. Авторизация ngrok настраивается штатным способом вне Git.

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now cashguard.service cashguard-tunnel.service
# Для сохранения user units после logout необходим Linger для пользователя.
loginctl show-user "$USER" -p Linger
```

Модель разворачивается отдельно. URL и её ключ доступны только backend; браузер знает лишь API приложения. Используйте `tools/smoke_api.py` с приватным файлом ключа для проверки 401, cookie, диапазонов видео и, с `--video`, реальной обработки MOV. Отчёт не включает ключи. Приватный `*.result.json` содержит кадры — не публикуйте его.

## Отзыв доступа и резервирование

Для отзыва ключа жюри замените `private/jury-api.key` новым случайным секретом ≥24 символов и перезапустите приложение. Это также отзывает старые браузерные сессии. Модельный и jury ключи независимы. Файл ключа приложения нужен только жюри/команде; модельный токен и SSH ключи им не передаются.

До обновления сохраняйте app/rules и текущую конфигурацию приватно. Исходные примеры и benchmark ответы хранятся отдельно от Git. Смена домена модели требует правки `MODEL_URL`, `MODEL_ALLOWED_HOSTS` и перезапуска. При недоступности модели сервис отказывает в приёме нового задания; скрытого fallback на другие AI API нет.
