# Интеграция приложения с маркетплейсом

## Обзор

Маркетплейс позволяет встраивать сторонние веб-приложения в интерфейс платформы через `<iframe>`.
При запуске приложения платформа автоматически передаёт ему `launch_token` — одноразовый токен,
с помощью которого ваше приложение может идентифицировать пользователя через OIDC.

---

## Регистрация приложения

Чтобы разместить приложение на маркетплейсе, необходимо пройти процесс регистрации.
После успешной регистрации вы получите:

| Параметр        | Пример |
|-----------------|--------|
| `client_id`     | `marketplace-_WE-92D2QodfG0BdCEQx5PPZNiP-OeDB` |
| `client_secret` | `us1lTLvOVXELbjFqfPmEwo0KqYpyFqXhPBkHVXK5tg3_6ECY3mo3rUCgs-sUTfKr` |

> **Важно:** `client_secret` показывается только один раз при создании.
> Сохраните его в надёжном месте. Восстановить его невозможно — только перевыпустить.
>
> Храните `client_secret` исключительно на бэкенде. Никогда не передавайте его в браузер.

Помимо этого вам нужно заранее зарегистрировать **redirect URI** — URL вашего приложения,
на который будет происходить редирект после авторизации.

---

## Что нужно реализовать на вашей стороне

Ваше приложение должно корректно работать внутри `<iframe>` и иметь два эндпоинта:

### Эндпоинт 1 — запуск и начало аутентификации

**Пример:** `/oidc/auth`

Это стартовая точка: именно этот URL платформа откроет в `<iframe>`.
Эндпоинт получает от платформы два query-параметра:
- `platform_user_id` — UUID пользователя платформы
- `launch_token` — одноразовый токен для OIDC авторизации (действует **5 минут**)

Задача эндпоинта — считать `launch_token` и инициировать OIDC-авторизацию: передать токен
на бэкенд, который начнёт процесс аутентификации.

### Эндпоинт 2 — завершение аутентификации (redirect URI)

**Пример:** `/oidc/callback`

Этот URL должен быть заранее зарегистрирован как `redirect_uri` при регистрации приложения.
После успешной авторизации наш сервер выполнит редирект на этот адрес, добавив в URL-фрагмент:
- `code` — одноразовый код для обмена на токены
- `id_token` — JWT с базовыми данными пользователя

Задача эндпоинта — извлечь `code` из фрагмента (`#code=...&id_token=...`) и передать его
на бэкенд для обмена на `access_token` (см. Шаг 3).

---

## Полный сценарий интеграции

### Шаг 1. Приложение открывается в iframe

Платформа открывает ваше приложение в `<iframe>`, передавая `launch_token` и `platform_user_id`
как query-параметры к вашему `launch_url`:

```
https://myapp.example.com/launch
  ?platform_user_id=6cda2c9f-d8ff-4571-a8f0-d10924047dc0
  &launch_token=oQD7q0oRyG9fqpVaU7tAx8de5NWPyaGba7gX_DBJ3tKsuMEde20oiRx8SdP6swGl
```

Ваш фронтенд читает `launch_token` из URL и передаёт его на ваш бэкенд.
Дальнейшие запросы к OIDC должны выполняться **только с бэкенда** — так `client_secret`
не попадает в браузер.

---

### Шаг 2. Авторизация — получение кода

Ваш бэкенд делает запрос к нашему OIDC-серверу:

```
GET https://platform.local/oidc/authorize
  ?client_id=marketplace-_WE-92D2QodfG0BdCEQx5PPZNiP-OeDB
  &scope=openid
  &response_type=code%20id_token
  &redirect_uri=https://myapp.example.com/oidc/callback
  &launch_token=oQD7q0oRyG9fqpVaU7tAx8de5NWPyaGba7gX_DBJ3tKsuMEde20oiRx8SdP6swGl
  &nonce=random-string-12345
```

| Параметр        | Описание |
|-----------------|----------|
| `client_id`     | Выданный вам идентификатор приложения |
| `scope`         | Всегда `openid` |
| `response_type` | Всегда `code id_token` |
| `redirect_uri`  | Должен совпадать с зарегистрированным при регистрации |
| `launch_token`  | Токен из query-параметров iframe |
| `nonce`         | Произвольная случайная строка для защиты от replay-атак |

**Ответ** — редирект `302` на ваш `redirect_uri` с фрагментом:

```
https://myapp.example.com/oidc/callback#code=Kf3mR8tN2pQ7vL9wX4yZ1aB6cD0eF5gH&id_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3BsYXRmb3JtLmxvY2FsIiwic3ViIjoiNmNkYTJjOWYtZDhmZi00NTcxLWE4ZjAtZDEwOTI0MDQ3ZGMwIiwiYXVkIjoibWFya2V0cGxhY2UtX1dFLTkyRDJRb2RmRzBCZENFUXg1UFBaTmlQLU9lREIiLCJleHAiOjE3Nzg0MzI4NDksImlhdCI6MTc3ODQyOTI0OSwibmFtZSI6ImxveCIsInBob25lIjoiKzc5Nzc3Nzc3Nzc3Iiwibm9uY2UiOiJyYW5kb20tc3RyaW5nLTEyMzQ1In0.signature
```

`id_token` — это подписанный JWT с базовыми данными пользователя. Его можно декодировать сразу,
не делая дополнительных запросов:

```json
{
  "iss": "https://marketplace.openschools.education",
  "sub": "6cda2c9f-d8ff-4571-a8f0-d10924047dc0",
  "aud": "marketplace-_WE-92D2QodfG0BdCEQx5PPZNiP-OeDB",
  "exp": 1778432849,
  "iat": 1778429249,
  "name": "username",
  "phone": "+79777777777",
  "nonce": "random-string-12345"
}
```

> **Одноразовость:** каждый `launch_token` можно использовать для авторизации только один раз.
> При повторном запросе с тем же токеном вернётся ошибка `400`.

---

### Шаг 3. Обмен кода на токены

Ваш бэкенд обменивает полученный `code` на `access_token` и `refresh_token`:

```bash
curl -X POST https://platform.local/oidc/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=Kf3mR8tN2pQ7vL9wX4yZ1aB6cD0eF5gH" \
  -d "redirect_uri=https://myapp.example.com/oidc/callback" \
  -d "client_id=marketplace-_WE-92D2QodfG0BdCEQx5PPZNiP-OeDB" \
  -d "client_secret=us1lTLvOVXELbjFqfPmEwo0KqYpyFqXhPBkHVXK5tg3_6ECY3mo3rUCgs-sUTfKr"
```

**Ответ `200 OK`:**

```json
{
  "token_type": "Bearer",
  "access_token": "CgXjMiQiPCC-Uki9Eqqk1kxAbVXPbVnSd0CrFWFtk8mY7PIEObKTWXbL",
  "expires_in": 3600,
  "scope": "openid",
  "refresh_token": "_TaarXjrUTDSx00oOSIA_iC21D9vWvGLVChpN3MXNpnha5yBUsyg17UX-UByGGOS",
  "id_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3BsYXRmb3JtLmxvY2FsIiwic3ViIjoiNmNkYTJjOWYtZDhmZi00NTcxLWE4ZjAtZDEwOTI0MDQ3ZGMwIiwiYXVkIjoibWFya2V0cGxhY2UtX1dFLTkyRDJRb2RmRzBCZENFUXg1UFBaTmlQLU9lREIiLCJleHAiOjE3Nzg0MzI4NDksImlhdCI6MTc3ODQyOTI0OSwibmFtZSI6ImxveCIsInBob25lIjoiKzc5Nzc3Nzc3Nzc3Iiwibm9uY2UiOiJwb2h1aSJ9.yUz7iXQ1-biAdeOdKLMCmr95NmDKO4pBMn79m_xKohU"
}
```

| Поле            | Описание |
|-----------------|----------|
| `access_token`  | Токен для запросов к нашему API. Действует **1 час** |
| `refresh_token` | Токен для продления сессии. Действует **30 дней** |
| `id_token`      | JWT с данными пользователя — тот же что в шаге 2 |
| `expires_in`    | Время жизни `access_token` в секундах |

---

### Шаг 4. Получение данных пользователя

Когда нужны актуальные данные профиля, используйте `access_token`:

```bash
curl https://platform.local/oidc/userinfo \
  -H "Authorization: Bearer CgXjMiQiPCC-Uki9Eqqk1kxAbVXPbVnSd0CrFWFtk8mY7PIEObKTWXbL"
```

**Ответ `200 OK`:**

```json
{
  "user": {
    "id": "6cda2c9f-d8ff-4571-a8f0-d10924047dc0",
    "name": "lox",
    "phone": "+79777777777",
    "profiles": [...]
  }
}
```

---

### Шаг 5. Обновление access_token

`access_token` действует 1 час. Когда он истёк, обновите его через `refresh_token`:

```bash
curl -X POST https://platform.local/oidc/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=_TaarXjrUTDSx00oOSIA_iC21D9vWvGLVChpN3MXNpnha5yBUsyg17UX-UByGGOS" \
  -d "client_id=marketplace-_WE-92D2QodfG0BdCEQx5PPZNiP-OeDB" \
  -d "client_secret=us1lTLvOVXELbjFqfPmEwo0KqYpyFqXhPBkHVXK5tg3_6ECY3mo3rUCgs-sUTfKr"
```

**Ответ `200 OK`:**

```json
{
  "token_type": "Bearer",
  "access_token": "NewAccessToken...",
  "expires_in": 3600,
  "scope": "openid",
  "refresh_token": "_TaarXjrUTDSx00oOSIA_iC21D9vWvGLVChpN3MXNpnha5yBUsyg17UX-UByGGOS",
  "id_token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

> `refresh_token` остаётся тем же самым — ротация не выполняется.
> Храните его в безопасном месте: он действует 30 дней.

---

## Справочник ошибок

| HTTP | Сообщение | Причина |
|------|-----------|---------|
| `400` | `Missing required parameters: ...` | Не переданы обязательные параметры в `/oidc/authorize` |
| `400` | `scope must include 'openid'` | Параметр `scope` не содержит `openid` |
| `400` | `Unsupported response_type: '...'. Expected 'code id_token'` | Неверный `response_type` |
| `400` | `launch_token has expired` | Токен запуска истёк (TTL 5 минут) |
| `400` | `launch_token has already been used` | Попытка использовать `launch_token` повторно |
| `403` | `redirect_uri is not registered for this client` | `redirect_uri` не совпадает с зарегистрированным |
| `403` | `launch_token does not belong to this client` | Токен выдан для другого приложения |
| `401` | `Invalid access_token` | Токен не найден |
| `401` | `access_token has expired` | Токен истёк — нужно обновить через `refresh_token` |
