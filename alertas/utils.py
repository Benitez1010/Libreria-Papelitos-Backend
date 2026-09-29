import threading
from django.core.mail import send_mail
from django.conf import settings
from .models import DestinatarioCorreo, HistorialAlerta

def enviar_alerta_async(producto_id, producto_nombre, categoria_nombre, ubicacion, saldo_actual, stock_minimo):
    """
    Función interna que procesa el correo de forma aislada, utilizando
    la plantilla HTML institucional de Librería Papelitos.
    """
    destinatarios = list(DestinatarioCorreo.objects.filter(activo=True).values_list('correo', flat=True))
    envio_exitoso = False
    
    if destinatarios:
        try:
            asunto = f"ALERTA DE STOCK CRÍTICO: {producto_nombre}"
            
            # Mensaje en texto plano (respaldo por si el cliente de correo no soporta HTML)
            mensaje_plano = (
                f"⚠️ AVISO AUTOMÁTICO DE INVENTARIO ⚠️\n\n"
                f"El artículo ha alcanzado su nivel crítico y requiere reabastecimiento.\n\n"
                f"• Producto: {producto_nombre}\n"
                f"• Categoría: {categoria_nombre}\n"
                f"• Saldo Actual Total: {saldo_actual} unidades\n"
                f"• Ubicación de la alerta: {ubicacion}\n"
                f"• Stock Mínimo Permitido: {stock_minimo} unidades\n\n"
                f"Este es un mensaje generado automáticamente por el sistema."
            )

            # Plantilla HTML adaptada del diseño de recuperación de contraseñas
            cuerpo_html = f"""
            <div style="background-color:#A3C9B8;padding:32px 16px;font-family:Arial,Helvetica,sans-serif;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center"
                     style="max-width:560px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.12);">
                <tr>
                  <td align="center" style="background-color:#ffffff;padding:28px 24px 12px 24px;">
                    <img src="{getattr(settings, 'LOGO_URL', '')}" alt="Librería Papelitos" width="180"
                         style="display:block;width:180px;max-width:60%;height:auto;">
                  </td>
                </tr>
                <tr>
                  <td style="background-color:#1E5631;height:6px;line-height:6px;font-size:0;">&nbsp;</td>
                </tr>
                <tr>
                  <td style="background-color:#EAF4EC;padding:32px 32px 24px 32px;">
                    <h1 style="margin:0 0 20px 0;color:#1E5631;font-size:22px;letter-spacing:1px;text-align:center;">
                      ⚠️ ALERTA DE STOCK CRÍTICO
                    </h1>
                    <p style="margin:0 0 24px 0;color:#37474F;font-size:15px;line-height:1.6;text-align:center;">
                      El siguiente artículo ha alcanzado su nivel crítico en el inventario y requiere reabastecimiento oportuno.
                    </p>
                    
                    <!-- Tarjeta de Detalles del Producto -->
                    <div style="background-color:#ffffff;border-left:4px solid #d32f2f;padding:16px;border-radius:4px;margin-bottom:24px;box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                        <p style="margin:0 0 8px 0;color:#37474F;font-size:15px;"><strong>Producto:</strong> {producto_nombre}</p>
                        <p style="margin:0 0 8px 0;color:#37474F;font-size:15px;"><strong>Categoría:</strong> {categoria_nombre}</p>
                        <p style="margin:0 0 8px 0;color:#37474F;font-size:15px;"><strong>Ubicación de la alerta:</strong> {ubicacion}</p>
                        <p style="margin:0 0 8px 0;color:#d32f2f;font-size:16px;"><strong>Saldo Actual Total:</strong> {saldo_actual} unidades</p>
                        <p style="margin:0;color:#78909C;font-size:14px;"><strong>Stock Mínimo Permitido:</strong> {stock_minimo} unidades</p>
                    </div>
                    
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center"
                           style="margin:0 auto 24px auto;">
                      <tr>
                        <td align="center" style="background-color:#1E5631;border-radius:8px;">
                          <a href="{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/productos"
                             style="display:inline-block;padding:15px 38px;color:#ffffff;font-size:16px;font-weight:bold;text-decoration:none;">
                            Ir al Inventario
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="background-color:#EAF4EC;padding:0 32px 28px 32px;">
                    <div style="border-top:1px solid #C5DFD0;padding-top:18px;">
                      <p style="margin:0;color:#78909C;font-size:12px;line-height:1.6;text-align:center;">
                        Este es un mensaje generado automáticamente por el sistema de inventario.<br>
                        Por favor, no responda a este correo.
                      </p>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="background-color:#1E5631;padding:16px 24px;">
                    <p style="margin:0;color:#EAF4EC;font-size:12px;letter-spacing:1px;">
                      LIBRERÍA PAPELITOS
                    </p>
                  </td>
                </tr>
              </table>
            </div>
            """
            
            send_mail(
                subject=asunto,
                message=mensaje_plano,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=destinatarios,
                html_message=cuerpo_html,
                fail_silently=False
            )
            envio_exitoso = True
        except Exception:
            # Falla silenciosa para evitar trabar el frontend
            envio_exitoso = False
    
    # Registro inmutable en la bitácora
    HistorialAlerta.objects.create(
        producto_id=producto_id,
        saldo_momento=saldo_actual,
        notificacion_enviada=envio_exitoso
    )

def disparar_alerta_email(producto_id, producto_nombre, categoria_nombre, ubicacion, saldo_actual, stock_minimo):
    """
    Invocador del hilo. Se pasan variables primitivas para evitar bloqueos del ORM.
    """
    hilo = threading.Thread(target=enviar_alerta_async, args=(
        producto_id, producto_nombre, categoria_nombre, ubicacion, saldo_actual, stock_minimo
    ))
    hilo.start()