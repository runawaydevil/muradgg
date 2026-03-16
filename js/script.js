(function() {
    const PER_PAGE = 15;
    let allPosts = [];
    let currentPage = 1;

    const blogContainer = document.getElementById('blog');

    // Carrega dados embutidos ou via JSON (vamos embutir no HTML inicialmente via update_posts.py)
    window.initBlog = function(postsData) {
        allPosts = postsData;

        // Router simples baseado em hash
        window.addEventListener('hashchange', router);
        router();
    };

    function router() {
        const hash = window.location.hash;
        if (hash.startsWith('#post/')) {
            const postId = hash.split('/')[1];
            renderPost(postId);
        } else {
            renderIndex(1);
        }
        // Scroll to top on navigation
        window.scrollTo(0, 0);
    }

    function renderIndex(page) {
        currentPage = page;
        const start = (page - 1) * PER_PAGE;
        const end = start + PER_PAGE;
        const pagePosts = allPosts.slice(start, end);
        const totalPages = Math.ceil(allPosts.length / PER_PAGE);

        if (allPosts.length === 0) {
            blogContainer.innerHTML = '<p style="text-align:center; color:var(--crt-muted);">Nenhuma postagem encontrada.</p>';
            return;
        }

        let html = '<div class="post-index">';
        pagePosts.forEach(post => {
            html += `
                <div class="post-index-item">
                    <a href="#post/${post.id}">${post.title}</a>
                    <span class="post-index-date">${post.date}</span>
                </div>
            `;
        });
        html += '</div>';

        if (totalPages > 1) {
            html += `
                <nav class="blog-pagination">
                    <a href="#" class="${currentPage === 1 ? 'blog-pagination-disabled' : ''}" id="prev-page">Anterior</a>
                    <span class="blog-pagination-info">Página ${currentPage} de ${totalPages}</span>
                    <a href="#" class="${currentPage === totalPages ? 'blog-pagination-disabled' : ''}" id="next-page">Próxima</a>
                </nav>
            `;
        }

        blogContainer.innerHTML = html;

        const prev = document.getElementById('prev-page');
        const next = document.getElementById('next-page');
        if (prev) prev.onclick = (e) => { e.preventDefault(); renderIndex(currentPage - 1); };
        if (next) next.onclick = (e) => { e.preventDefault(); renderIndex(currentPage + 1); };
    }

    function renderPost(id) {
        const post = allPosts.find(p => p.id == id);
        if (!post) {
            blogContainer.innerHTML = '<p>Post não encontrado.</p><a href="#" class="back-link">← Voltar ao índice</a>';
            return;
        }

        blogContainer.innerHTML = `
            <article class="blog-post">
                <a href="#" class="back-link">← Voltar ao índice</a>
                <h2>${post.title}</h2>
                <p class="blog-date">${post.date}</p>
                <div class="blog-body">${post.body}</div>
            </article>
        `;
    }
})();
