from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.kb import bp
from app.models.kb import KBArticle, KBCategory


# ── Public / Agent Views ────────────────────────────────────────────────────

@bp.route('/')
@login_required
def index():
    categories = (KBCategory.query
                  .filter_by(is_active=True)
                  .order_by(KBCategory.order, KBCategory.name)
                  .all())
    # recent + popular articles
    recent = (KBArticle.query
              .filter_by(is_published=True)
              .order_by(KBArticle.created_at.desc())
              .limit(5).all())
    popular = (KBArticle.query
               .filter_by(is_published=True)
               .order_by(KBArticle.views.desc())
               .limit(5).all())
    return render_template('kb/index.html',
                           categories=categories,
                           recent=recent,
                           popular=popular)


@bp.route('/article/<slug>')
@login_required
def article(slug):
    art = KBArticle.query.filter_by(slug=slug).first_or_404()
    if not art.is_published and not current_user.has_role('Admin'):
        abort(404)
    # Increment view count
    art.views += 1
    db.session.commit()
    # Related: same category, published
    related = []
    if art.category_id:
        related = (KBArticle.query
                   .filter(KBArticle.category_id == art.category_id,
                           KBArticle.id != art.id,
                           KBArticle.is_published == True)
                   .order_by(KBArticle.views.desc())
                   .limit(4).all())
    return render_template('kb/article.html', article=art, related=related)


@bp.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    results = []
    if q:
        like = f'%{q}%'
        results = (KBArticle.query
                   .filter(KBArticle.is_published == True)
                   .filter(or_(KBArticle.title.ilike(like),
                               KBArticle.content.ilike(like),
                               KBArticle.tags.ilike(like)))
                   .order_by(KBArticle.views.desc())
                   .all())
    return render_template('kb/search.html', results=results, query=q)


@bp.route('/category/<slug>')
@login_required
def category(slug):
    cat = KBCategory.query.filter_by(slug=slug, is_active=True).first_or_404()
    articles = (KBArticle.query
                .filter_by(category_id=cat.id, is_published=True)
                .order_by(KBArticle.updated_at.desc())
                .all())
    return render_template('kb/category.html', category=cat, articles=articles)
