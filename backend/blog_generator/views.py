from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
import json
from pytube import YouTube
import assemblyai as aai
from decouple import config
import os
import yt_dlp
from .models import BlogPost
import openai
aai.settings.api_key = config('AssemblyAPIKey')
transcriber = aai.Transcriber()

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
            
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error':'Invalid data sent'}, status=400)
        
    
        # get trasncript and video title
        trascription, video_title = get_transcription(yt_link)
        
        if not trascription:
            return JsonResponse({'error':'Faile to get transcript'}, status=400)
   

        # use openai to generate the blog
        blog_content = generate_blog_from_transcription(transcription=trascription)
        
        if not blog_content:
            return JsonResponse({'error':'Failed to generate transcript'}, status=400)
        # save blog article to data base
        new_blog_article = BlogPost.objects.create(user= request.user,
                                                   youtube_title= video_title,
                                                   youtube_link=yt_link,
                                                   generated_content = blog_content)
        new_blog_article.save()
        # return blog article as response
        return JsonResponse({'content' : blog_content})
    else:
        return JsonResponse({'error':'Invalid request method'}, status=405)

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

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

def generate_blog_from_transcription(transcription):
    openai.api_key = config("OpenAIAPIkey")
    
    prompt = f"Based on the following transcript from a Youtube Video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a proper blog article:\n\n{transcription}\n\nArticle:"
    response = openai.completions.create(
        model= "gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=1000
    )
    generated_content = response.choices[0].text.strip()
    return generated_content

def download_audio_with_yt_dlp(link):
    try:
        # Configuration for yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{settings.MEDIA_ROOT}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        # Download audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            audio_file = os.path.join(settings.MEDIA_ROOT, f"{info_dict['title']}.mp3")
            video_title = info_dict.get('title', 'Unknown Title')  # Extract title safely
            
            return audio_file, video_title

    except yt_dlp.utils.DownloadError as e:
        print(f"yt-dlp DownloadError: {e}")
        raise ValueError("Failed to download the audio.")
    except Exception as e:
        print(f"Error: {e}")
        raise ValueError("An unexpected error occurred while downloading the audio.")
 
def download_audio(link):
    try:
        # Initialize YouTube object
        yt = YouTube(link)
        
        # Fetch audio-only stream
        video = yt.streams.filter().first()
        if not video:
            raise ValueError("No audio stream available for this video.")
        
        # Download audio file
        out_file = video.download(output_path=settings.MEDIA_ROOT)

        # Rename file to .mp3
        base, ext = os.path.splitext(out_file)
        new_file = base + '.mp3'
        os.rename(out_file, new_file)

        return new_file
    except KeyError as e:
        print(f"KeyError: Unable to fetch video details - {e}")
        raise ValueError("Failed to fetch video details. The video may be inaccessible.")
    except Exception as e:
        print(f"Error downloading audio: {e}")
        raise ValueError("An error occurred while downloading the audio.")

def get_transcription(yt_link):
    audio_file, video_title = download_audio_with_yt_dlp(yt_link)
    transcript = transcriber.transcribe(audio_file)
    if not transcript or not transcript.text:
        raise ValueError("Failed to transcribe audio.")

    # Define the transcript file path
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    transcript_file_path = os.path.join(settings.MEDIA_ROOT, f"{base_name}_transcript.txt")

    # Save the transcript to a file
    try:
        with open(transcript_file_path, 'w', encoding='utf-8') as file:
            file.write(transcript.text)
        print(f"Transcript saved at {transcript_file_path}")
    except Exception as e:
        print(f"Error saving transcript: {e}")
        raise ValueError("An error occurred while saving the transcript.")
    
    return transcript.text, video_title

def yt_title(link):
    try:
        yt = YouTube(link)
        title = yt.title
        return title
    except KeyError as e:
        print(f"KeyError while fetching title: {e}")
        return "Unknown Title"
    except Exception as e:
        print(f"Error while fetching YouTube title: {e}")
        return "Unknown Title"

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