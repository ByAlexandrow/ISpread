from django.utils.timezone import now


def get_post(posts):
    return posts.select_related(
        'author', 'category', 'location'
    ).filter(
        is_published=True,
        category__is_published=True,
        pub_date__date__lt=now()
    )
