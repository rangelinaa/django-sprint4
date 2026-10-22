
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db import models

from .forms import CommentForm, PostForm, UserEditForm
from .models import Category, Comment, Post, User


def get_published_posts():
    return (
        Post.objects
        .filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )
        .select_related('category', 'location', 'author')
        .annotate(comment_count=models.Count('comments'))
        .order_by('-pub_date')
    )


def index(request):
    posts = get_published_posts()
    page_obj = Paginator(posts, 10).get_page(request.GET.get('page'))
    return render(request, 'blog/index.html', {
    'page_obj': page_obj,
    'post_list': page_obj,
    })

def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    posts = get_published_posts().filter(category=category)
    page_obj = Paginator(posts, 10).get_page(request.GET.get('page'))
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': page_obj,
        'post_list': page_obj,
    })


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('category', 'location', 'author'),
        pk=post_id,
    )
    if not post.is_published or post.pub_date > timezone.now():
        if request.user != post.author:
            from django.http import Http404
            raise Http404
    if post.category and not post.category.is_published:
        if request.user != post.author:
            from django.http import Http404
            raise Http404
    return render(request, 'blog/detail.html', {
        'post': post,
        'comments': post.comments.select_related('author'),
        'form': CommentForm(),
    })


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.id)
    form = PostForm(
        request.POST or None,
        request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.id)
    return render(request, 'blog/create.html', {
        'form': form,
        'is_edit': True,
        'post': post,
    })


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    return render(request, 'blog/create.html', {
        'post': post,
        'delete_mode': True,
    })


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = (
        Post.objects
        .filter(author=profile_user)
        .select_related('category', 'location', 'author')
        .annotate(comment_count=models.Count('comments'))
        .order_by('-pub_date')
    )

    page_obj = Paginator(posts, 10).get_page(request.GET.get('page'))
    return render(request, 'blog/profile.html', {
        'profile': profile_user,
        'page_obj': page_obj,
        'post_list': page_obj,
    })


@login_required
def edit_profile(request):
    form = UserEditForm(
        request.POST or None,
        instance=request.user,
    )
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(get_published_posts(), pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect('blog:post_detail', post_id=post.id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id
    )
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {
        'form': form,
        'comment': comment,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id
    )
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {
        'comment': comment,
        'delete_mode': True,
    })
