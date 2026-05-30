from .models import DzienPracy
from datetime import date

def dzien_pracy_status(request):
    if request.user.is_authenticated:
        dzien = DzienPracy.objects.filter(user=request.user, data=date.today()).first()
        is_open = dzien and dzien.czas_zamkniecia is None
        return {'is_day_started': is_open}
    return {'is_day_started': False}
