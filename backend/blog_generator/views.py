from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['userPassword']
        
        user = authenticate(request, username = username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid Username or Password"
            return render(request, 'login.html', {'error_message' : error_message} )
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['useremail']
        password = request.POST['userPassword']
        repeat_password = request.POST['userConfirmPassword']
        if password == repeat_password:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')

            except:
                error_message = 'Error Creating Accont'
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message' : error_message} )
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')