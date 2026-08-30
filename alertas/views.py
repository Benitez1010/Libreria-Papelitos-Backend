from rest_framework import viewsets, status
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from .models import DestinatarioCorreo, HistorialAlerta
from .serializers import DestinatarioCorreoSerializer, HistorialAlertaSerializer

class DestinatarioCorreoViewSet(viewsets.ModelViewSet):
    queryset = DestinatarioCorreo.objects.all()
    serializer_class = DestinatarioCorreoSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        correo_destino = serializer.validated_data['correo']
        
        try:
            send_mail(
                subject='Validación de Alertas - Librería Papelitos',
                message='Este es un mensaje automático. Tu correo ha sido configurado para recibir alertas de stock crítico.',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[correo_destino],
                fail_silently=False,
            )
            mensaje = "Correo de prueba enviado exitosamente."
        except Exception as e:
            mensaje = "Registro guardado, pero falló la conexión con Gmail."

        headers = self.get_success_headers(serializer.data)
        return Response(
            {"data": serializer.data, "mensaje": mensaje}, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )

class HistorialAlertaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistorialAlerta.objects.all()
    serializer_class = HistorialAlertaSerializer