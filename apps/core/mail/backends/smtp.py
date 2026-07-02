import ssl
from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend


class EmailBackend(DjangoEmailBackend):
    """SMTP backend that tolerates the environment's certificate issues during development."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('use_tls', True)
        super().__init__(*args, **kwargs)

    def open(self):
        if self.connection:
            return False

        self.connection = self.connection_class(
            self.host,
            self.port,
            timeout=self.timeout,
        )
        self.connection.set_debuglevel(self.fail_silently)

        if self.use_tls:
            self.connection.ehlo()
            self.connection.starttls(context=ssl._create_unverified_context())
            self.connection.ehlo()

        if self.username and self.password:
            self.connection.login(self.username, self.password)

        return True
