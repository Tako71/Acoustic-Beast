from django.urls import path
from . import views

urlpatterns = [
    path('',                       views.home,          name='home'),
    path('docs/',                  views.docs,          name='docs'),
    path('faq/',                   views.faq,           name='faq'),
    path('calculate/',             views.calculate_view, name='calculate'),
    path('result/<int:pk>/',       views.result_view,   name='result'),
    path('result/<int:pk>/pdf/',   views.download_pdf,  name='download_pdf'),
    path('history/',               views.history_view,  name='history'),
]
