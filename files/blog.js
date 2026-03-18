/**
 * Blog dinâmico - Carrega posts de posts.json
 * Mantém a estética CRT/terminal do murad.gg
 */
(function() {
  'use strict';

  let postsData = [];
  let config = {};
  let currentPage = 1;
  let totalPages = 1;

  // Elementos do DOM
  const blogSection = document.getElementById('blog');
  
  // Inicialização
  async function init() {
    try {
      const response = await fetch('files/posts.json');
      if (!response.ok) throw new Error('Falha ao carregar posts.json');
      
      const data = await response.json();
      config = data.config || { posts_per_page: 10 };
      postsData = data.posts || [];
      totalPages = Math.max(1, Math.ceil(postsData.length / config.posts_per_page));
      
      renderBlog();
      setupRouting();
    } catch (error) {
      console.error('Erro ao carregar posts:', error);
      if (blogSection) {
        blogSection.innerHTML = '<p style="color: var(--crt-muted);">Nenhum post encontrado.</p>';
      }
    }
  }

  // Renderiza a estrutura do blog
  function renderBlog() {
    if (!blogSection || postsData.length === 0) return;

    let html = '';
    
    // Lista de posts
    html += '<div id="blog-list">';
    postsData.forEach(post => {
      html += `
        <div class="blog-list-item">
          <span class="blog-list-date">${escapeHtml(post.date)}</span>
          <span class="blog-list-reading-time">~${post.reading_time} min</span>
          <a href="#${escapeHtml(post.slug)}">${escapeHtml(post.title)}</a>
        </div>`;
    });
    html += '</div>';

    // Paginação
    if (totalPages > 1) {
      html += `
        <div id="blog-pagination" class="blog-pagination">
          <a id="pagination-prev" href="javascript:window.blogPrevPage()" class="pagination-btn">&lt;-- Anterior</a>
          <span id="pagination-info" class="pagination-info">1/${totalPages}</span>
          <a id="pagination-next" href="javascript:window.blogNextPage()" class="pagination-btn">Próximo --&gt;</a>
        </div>`;
    }

    // Container de posts individuais
    html += '<div id="blog-posts-container" style="display:none;"></div>';

    blogSection.innerHTML = html;
  }

  // Mostra página específica da lista
  function showPage(page) {
    currentPage = page;
    const items = document.querySelectorAll('.blog-list-item');
    const start = (page - 1) * config.posts_per_page;
    const end = start + config.posts_per_page;

    items.forEach((item, i) => {
      item.style.display = (i >= start && i < end) ? 'block' : 'none';
    });

    updatePaginationButtons();
  }

  function updatePaginationButtons() {
    const prevBtn = document.getElementById('pagination-prev');
    const nextBtn = document.getElementById('pagination-next');
    const pageInfo = document.getElementById('pagination-info');

    if (prevBtn) prevBtn.style.visibility = currentPage > 1 ? 'visible' : 'hidden';
    if (nextBtn) nextBtn.style.visibility = currentPage < totalPages ? 'visible' : 'hidden';
    if (pageInfo) pageInfo.textContent = `${currentPage}/${totalPages}`;
  }

  // Renderiza um post individual
  function renderPost(slug) {
    const post = postsData.find(p => p.slug === slug);
    if (!post) return null;

    return `
      <article class="blog-post" id="${escapeHtml(post.slug)}">
        <div class="blog-nav"><a href="#">&lt;-- Voltar</a></div>
        <h2>${escapeHtml(post.title)}</h2>
        <p class="blog-date">${escapeHtml(post.date)} · ~${post.reading_time} min de leitura</p>
        <div class="blog-body">${post.html}</div>
      </article>`;
  }

  // Roteamento baseado em hash
  function route() {
    const hash = window.location.hash.substring(1);
    const blogList = document.getElementById('blog-list');
    const postsContainer = document.getElementById('blog-posts-container');
    const pagination = document.getElementById('blog-pagination');

    if (!hash) {
      // Mostra lista de posts
      if (blogList) blogList.style.display = 'block';
      if (postsContainer) {
        postsContainer.style.display = 'none';
        postsContainer.innerHTML = '';
      }
      if (pagination) pagination.style.display = totalPages > 1 ? 'flex' : 'none';
      showPage(currentPage);
    } else {
      // Mostra post individual
      if (blogList) blogList.style.display = 'none';
      if (pagination) pagination.style.display = 'none';
      
      if (postsContainer) {
        const postHtml = renderPost(hash);
        if (postHtml) {
          postsContainer.innerHTML = postHtml;
          postsContainer.style.display = 'block';
        } else {
          // Post não encontrado, volta para lista
          window.location.hash = '';
          return;
        }
      }
    }
    
    window.scrollTo(0, 0);
  }

  function setupRouting() {
    window.addEventListener('hashchange', route);
    route(); // Rota inicial
  }

  // Funções globais para paginação
  window.blogPrevPage = function() {
    if (currentPage > 1) showPage(currentPage - 1);
  };

  window.blogNextPage = function() {
    if (currentPage < totalPages) showPage(currentPage + 1);
  };

  // Utilitário para escapar HTML
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Inicia quando o DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
