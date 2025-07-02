from neomodel import StructuredRel, IntegerProperty, StringProperty


class PipeMain(StructuredRel):
    tag = IntegerProperty(index=True, required=True)
    pipe_type = StringProperty(index=True, required=True)
    # length = IntegerProperty(required=True)
