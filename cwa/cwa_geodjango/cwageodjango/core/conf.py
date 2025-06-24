import configparser
from types import SimpleNamespace
from itertools import chain
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from .validators import ConfigValidator


class AppConf:
    def __init__(self, conf_file: str):
        """Set the config params from the conf file

        https://stackoverflow.com/a/26859985
        """

        parser = configparser.ConfigParser()

        with open(conf_file) as lines:
            lines = chain(("[app_config]",), lines)  # This line does the trick.
            parser.read_file(lines)

        self._validate_config(parser["app_config"])


    def _validate_config(self, parser_config):
        config = ConfigValidator(parser_config)
        is_valid = config.is_valid()

        if not is_valid:
            raise ValidationError(
                [
                    ValidationError(
                        _("Invalid or missing: '%(value)s' - %(error)s"),
                        params={"value": value, "error": error[0]},
                    )
                    for value, error in config.errors.items()
                ]
            )

        self.validated_config = SimpleNamespace(**config.cleaned_data)
