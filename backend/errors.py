from flask import render_template


def render_error_template(icon, title, message, code):
    return render_template(
        "error.html",
        icon_class=icon,
        error_title=title,
        error_message=message,
        error_code=code
    ), code


def bad_request(e):
    return render_error_template(
        "fas fa-exclamation-circle",
        "Неверный запрос",
        "Сервер не может обработать ваш запрос из-за неверного синтаксиса.",
        400
    )


def unauthorized(e):
    return render_error_template(
        "fas fa-lock",
        "Не авторизован",
        "Для доступа к этой странице требуется авторизация.",
        401
    )


def forbidden(e):
    return render_error_template(
        "fas fa-ban",
        "Доступ запрещен",
        "У вас нет прав для доступа к этой странице.",
        403
    )


def not_found(e):
    return render_error_template(
        "fas fa-exclamation-triangle",
        "Страница не найдена",
        "Похоже, страница, которую вы ищете, не существует или была перемещена.",
        404
    )


def method_not_allowed(e):
    return render_error_template(
        "fas fa-ban",
        "Метод не разрешен",
        "Используемый метод HTTP не поддерживается для этого URL.",
        405
    )


def not_acceptable(e):
    return render_error_template(
        "fas fa-times-circle",
        "Неприемлемо",
        "Сервер не может предоставить ответ в соответствии с заголовками Accept.",
        406
    )


def request_timeout(e):
    return render_error_template(
        "fas fa-clock",
        "Время ожидания истекло",
        "Сервер ожидал запрос в течение слишком долгого времени.",
        408
    )


def conflict(e):
    return render_error_template(
        "fas fa-exclamation",
        "Конфликт",
        "Запрос конфликтует с текущим состоянием сервера.",
        409
    )


def gone(e):
    return render_error_template(
        "fas fa-trash-alt",
        "Удалено",
        "Запрашиваемый ресурс больше не доступен.",
        410
    )


def length_required(e):
    return render_error_template(
        "fas fa-ruler",
        "Требуется длина",
        "Заголовок Content-Length не определен.",
        411
    )


def precondition_failed(e):
    return render_error_template(
        "fas fa-check-circle",
        "Условие не выполнено",
        "Одно или несколько условий запроса не выполнены.",
        412
    )


def payload_too_large(e):
    return render_error_template(
        "fas fa-weight-hanging",
        "Слишком большой объем данных",
        "Запрос превышает ограничение по размеру.",
        413
    )


def uri_too_long(e):
    return render_error_template(
        "fas fa-link",
        "Слишком длинный URL",
        "Запрошенный URL слишком длинный для обработки.",
        414
    )


def unsupported_media_type(e):
    return render_error_template(
        "fas fa-file-alt",
        "Неподдерживаемый тип данных",
        "Формат запроса не поддерживается сервером.",
        415
    )


def range_not_satisfiable(e):
    return render_error_template(
        "fas fa-arrows-alt-h",
        "Диапазон не выполним",
        "Запрошенный диапазон не может быть выполнен.",
        416
    )


def expectation_failed(e):
    return render_error_template(
        "fas fa-times",
        "Ожидание не выполнено",
        "Сервер не может выполнить требования заголовка Expect.",
        417
    )


def im_a_teapot(e):
    return render_error_template(
        "fas fa-coffee",
        "Я чайник",
        "Сервер отказывается варить кофе, потому что он чайник.",
        418
    )


def misdirected_request(e):
    return render_error_template(
        "fas fa-exchange-alt",
        "Неправильное направление",
        "Запрос был направлен на сервер, который не может дать ответ.",
        421
    )


def unprocessable_entity(e):
    return render_error_template(
        "fas fa-database",
        "Необрабатываемая сущность",
        "Запрос содержит семантические ошибки.",
        422
    )


def locked(e):
    return render_error_template(
        "fas fa-lock",
        "Заблокировано",
        "Ресурс, к которому вы пытаетесь получить доступ, заблокирован.",
        423
    )


def failed_dependency(e):
    return render_error_template(
        "fas fa-unlink",
        "Неудачная зависимость",
        "Запрос не выполнен из-за неудачной зависимости.",
        424
    )


def precondition_required(e):
    return render_error_template(
        "fas fa-check-double",
        "Требуется условие",
        "Исходный сервер требует, чтобы запрос был условным.",
        428
    )


def too_many_requests(e):
    return render_error_template(
        "fas fa-stopwatch",
        "Слишком много запросов",
        "Вы отправили слишком много запросов за короткое время.",
        429
    )


def headers_too_large(e):
    return render_error_template(
        "fas fa-heading",
        "Заголовки слишком большие",
        "Заголовки запроса слишком большие для обработки сервером.",
        431
    )


def legal_unavailable(e):
    return render_error_template(
        "fas fa-gavel",
        "Юридически недоступно",
        "Доступ к ресурсу ограничен по юридическим причинам.",
        451
    )


def internal_error(e):
    return render_error_template(
        "fas fa-server",
        "Ошибка сервера",
        "На сервере произошла непредвиденная ошибка. Мы уже работаем над её устранением.",
        500
    )


def not_implemented(e):
    return render_error_template(
        "fas fa-code",
        "Не реализовано",
        "Сервер не поддерживает функциональность, необходимую для выполнения запроса.",
        501
    )


def bad_gateway(e):
    return render_error_template(
        "fas fa-network-wired",
        "Ошибка шлюза",
        "Сервер, действуя как шлюз или прокси, получил недопустимый ответ.",
        502
    )


def service_unavailable(e):
    return render_error_template(
        "fas fa-tools",
        "Сервис недоступен",
        "Сервер временно не может обрабатывать запросы. Пожалуйста, попробуйте позже.",
        503
    )


def gateway_timeout(e):
    return render_error_template(
        "fas fa-clock",
        "Время ожидания шлюза",
        "Сервер не получил своевременного ответа.",
        504
    )


def http_version_not_supported(e):
    return render_error_template(
        "fas fa-code-branch",
        "Версия HTTP не поддерживается",
        "Сервер не поддерживает версию протокола HTTP, используемую в запросе.",
        505
    )
