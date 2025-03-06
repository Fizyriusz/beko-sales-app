from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('produkty/', include('produkty.urls')),
    path('', lambda request: HttpResponseRedirect('/produkty/')),  # Przekierowanie do /produkty/, gdzie będzie widok home
]
