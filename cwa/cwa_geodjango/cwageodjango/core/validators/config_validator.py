from django import forms
from django.core.exceptions import ValidationError


class ConfigValidator(forms.Form):
    method = forms.CharField(max_length=23, required=True)
    neoj4_point = forms.BooleanField(required=False)
    srid = forms.IntegerField(required=True)
    batch_size = forms.IntegerField(required=True)
    chunk_size = forms.IntegerField(required=False)
    query_limit = forms.IntegerField(required=False)
    query_offset = forms.IntegerField(required=False)
    parallel = forms.BooleanField(required=False)
    thread_count = forms.IntegerField(required=False)
    processor_count = forms.IntegerField(required=False)
    inpfile = forms.CharField(max_length=256, required=False)
    outputfile = forms.CharField(max_length=256, required=False)
    dma_codes = forms.CharField(max_length=256, required=False)
    utility_names = forms.CharField(max_length=256, required=False)
    wntr_simulation_timestep_hours = forms.FloatField(required=False)
    wntr_simulation_length_hours = forms.FloatField(required=False)

    #    connection_distance_tolerance = forms.FloatField(required=True) # distance in meters

    def clean(self):
        cleaned_data = super().clean()
        self.validate_parallel(cleaned_data)
        self.validate_outputfile(cleaned_data)

    def validate_parallel(self, cleaned_data):
        """
        Validates the 'parallel', 'thread_count', and 'processor_count' fields in the cleaned data.

        Parameters:
            cleaned_data (dict): Cleaned data containing configuration parameters.

        Raises:
            ValidationError: If 'parallel' is True and either 'thread_count' or 'processor_count' is not specified.

        """
        parallel = cleaned_data.get("parallel")
        thread_count = cleaned_data.get("processor_count")
        processor_count = cleaned_data.get("processor_count")

        if parallel and not (thread_count or processor_count):
            raise ValidationError(
                "If parallel is set to 'True' both 'thread_count' and 'processor_count' must be specified."
            )

    def validate_outputfile(self, cleaned_data):
        """
        Validates the 'outputfile' field based on the 'method' field in the cleaned data.

        Parameters:
            cleaned_data (dict): Cleaned data containing configuration parameters.

        Raises:
            ValidationError: If 'method' is 'neo4j2wntrjson' or 'neo4j2wntrinp' and 'outputfile' is not specified.

        """
        method = cleaned_data.get("method")
        outputfile = cleaned_data.get("outputfile")

        if method in ("neo4j2wntrjson", "neo4j2wntrinp") and not outputfile:
            raise ValidationError(
                "If 'method' is 'neo4j2wntrjson' or 'neo4j2wntrinp', 'outputfile' must be specified."
            )

    def validate_inpfile(self, cleaned_data):
        """
        Validates the 'inpfile' field based on the 'method' field in the cleaned data.

        Parameters:
            cleaned_data (dict): Cleaned data containing configuration parameters.

        Raises:
            ValidationError: If 'method' is 'inp2hydaulic' and 'inpfile' is not specified.

        """
        method = cleaned_data.get("method")
        inpfile = cleaned_data.get("inpfile")

        if method in ("inp2hydaulic") and not inpfile:
            raise ValidationError(
                "If 'method' is 'inp2hydaulic', 'inpfile' must be specified."
            )

    def validate_time_parameters(self, cleaned_data):
        """
        Validates the 'wntr_simulation_timestep_hours' and 'wntr_simulation_length_hours' fields based
        on the 'method' field in the cleaned data.

        Parameters:
            cleaned_data (dict): Cleaned data containing configuration parameters.

        Raises:
            ValidationError: If 'method' is 'inp2hydaulic' or 'neo4j2wntrinp' or 'neo4j2wntrjson'
            and 'wntr_simulation_timestep_hours' or 'wntr_simulation_length_hours' is not specified.

        """
        method = cleaned_data.get("method")
        wntr_simulation_timestep_hours = cleaned_data.get("wntr_simulation_timestep_hours")
        wntr_simulation_length_hours = cleaned_data.get("wntr_simulation_length_hours")

        if method in ("inp2hydaulic",
                      "neo4j2wntrinp",
                      "neo4j2wntrjson") and not wntr_simulation_timestep_hours or not wntr_simulation_length_hours:
            raise ValidationError(
                "If 'method' is 'inp2hydaulic', 'neo4j2wntrinp', or 'neo4j2wntrjson', "
                "'wntr_simulation_timestep_hours' and 'wntr_simulation_length_hours' must be specified."
            )

    def clean_dma_codes(self):

        data = self.cleaned_data.get("dma_codes")

        if not data:
            return None

        # TODO: add explicit exception handles
        try:
            dma_codes = data.split(",")
            dma_codes = [code.strip() for code in dma_codes]
        except:
            raise ValidationError("Incorrect format for dma_codes")

        return dma_codes

    def clean_utility_names(self):

        data = self.cleaned_data.get("utility_names")

        if not data:
            return None

        # TODO: add explicit exception handles
        try:
            utility_names = data.split(",")
            utility_names = [name.strip() for name in utility_names]
        except:
            raise ValidationError("Incorrect format for utility_names")

        return utility_names

