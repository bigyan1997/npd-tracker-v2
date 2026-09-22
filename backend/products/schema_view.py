from rest_framework.response import Response
from rest_framework.views import APIView

from . import fields_schema as schema


class SchemaView(APIView):
    def get(self, request):
        return Response({
            "fields": schema.FIELDS,
            "sections": schema.SECTIONS,
            "pipelineFields": [f["key"] for f in schema.PIPELINE_FIELDS],
        })
