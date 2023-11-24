from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (CreateView, UpdateView, DeleteView,
                                  ListView, DetailView)
from django.urls import reverse_lazy, reverse
from django.utils.timezone import now

from .functions import get_post
from .models import Post, Category, Comment
from .forms import PostForm, CommentForm, EditProfileForm

User = get_user_model()


class PostMixin():
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'


class IndexListView(ListView):
    """Главная страница"""

    model = Post
    paginate_by = 10
    template_name = 'blog/index.html'

    def get_queryset(self):
        return get_post(Post.objects).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')


class PostDetailView(LoginRequiredMixin, DetailView):
    """Детали публикации"""

    model = Post
    pk_url_kwarg = 'post_id'
    form_class = PostForm
    template_name = 'blog/detail.html'

    def get_object(self, queryset=None):
        self.post = get_object_or_404(Post, id=self.kwargs['post_id'])
        if self.post.author == self.request.user:
            return self.post
        return get_object_or_404(
            self.model.objects.select_related(
                'location', 'author', 'category',
            ).filter(
                is_published=True,
                pub_date__lte=now(),
                category__is_published=True
            ),
            id=self.kwargs['post_id'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = (
            self.get_object().comments.select_related('author')
        )
        return context


class CategoryPostsView(ListView):
    """Категория публикаций"""

    model = Post
    paginate_by = 10
    template_name = 'blog/category.html'

    def get_queryset(self):
        return get_post(Post.objects).filter(
            category__slug=self.kwargs['category_slug'],
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category,
            is_published=True,
            slug=self.kwargs['category_slug'],
        )
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Редактироание профиля"""

    form_class = EditProfileForm
    template_name = 'blog/user.html'
    success_url = reverse_lazy('blog:index')

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user})


class ProfileListView(ListView):
    """Страница пользователя"""

    model = Post
    paginate_by = 10
    template_name = 'blog/profile.html'

    def get_queryset(self):
        self.author = get_object_or_404(User, username=self.kwargs['username'])
        return Post.objects.select_related(
            'author', 'location', 'category',
        ).filter(
            author=self.author
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(
            User, username=self.kwargs['username'],
        )
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание публикации"""

    form_class = PostForm
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user})


class PostEditView(LoginRequiredMixin, PostMixin, UpdateView):
    """Редактирование комментария"""

    form_class = PostForm

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != self.request.user:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', args=(self.kwargs['post_id'],))


class PostDeleteView(LoginRequiredMixin, PostMixin, DeleteView):
    """Удаление публикации"""

    success_url = reverse_lazy('blog:index')

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context


class CreateCommentView(LoginRequiredMixin, CreateView):
    """Добавление комментария"""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    post_obj = None

    def dispatch(self, request, *args, **kwargs):
        self.post_obj = get_object_or_404(
            Post, id=self.kwargs['post_id']
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.comments = self.post_obj
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.kwargs['post_id']})


class CommentEditView(UpdateView):
    """Редактирование комментария"""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    form_class = CommentForm

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            return redirect('blog:post_detail',
                            post_id=self.kwargs['comment_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', args=(self.kwargs['comment_id'],))


class CommentDeleteView(DeleteView):
    """Удаление комментария"""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            return redirect('blog:post_detail',
                            post_id=self.kwargs['comment_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', args=(self.kwargs['comment_id'],))
