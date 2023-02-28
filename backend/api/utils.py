from io import BytesIO
from django.conf import settings
from django.db.models import Sum
from django.http import FileResponse
from recipes.models import RecipeIngredient
from reportlab import rl_config
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

def download_ingredients_pdf(request):
    buffer = BytesIO()
    rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/data')
    pdfmetrics.registerFont(TTFont('FreeSans', 'FreeSans.ttf'))
    pdf_obj = canvas.Canvas(buffer, pagesize=A4)
    pdf_obj.setFont('FreeSans', 20)
    queryset = RecipeIngredient.objects.filter(
        recipe__shopping_cart__user=request.user).values(
            'ingredient__name',
            'ingredient__measurement_unit').annotate(
                total_amount=Sum('amount'))
    pdf_title = 'Список покупок'
    title_x_coord = 260
    title_y_coord = 800
    x_coord = 50
    y_coord = 780
    if queryset:
        pdf_obj.drawCentredString(title_x_coord, title_y_coord, pdf_title)
        for item in queryset:
            pdf_obj.setFontSize(14)
            pdf_obj.drawString(
                x_coord, y_coord,
                f"{item['ingredient__name']} - "
                f"{item['total_amount']} "
                f"{item['ingredient__measurement_unit']}"
            )
            y_coord -= 15
            if y_coord < 30:
                pdf_obj.showPage()
                y_coord = 800
            else:
                pdf_obj.drawCentredString(
                    title_x_coord,
                    title_y_coord,
                    'Список покупок пуст.')
            pdf_obj.showPage()
            pdf_obj.save()
            buffer.seek(0)
            return FileResponse(buffer, as_attachment=True,
                                filename='shopping_cart.pdf')
