# murad.gg - Blog Pessoal CRT

Este é um blog pessoal com uma estética CRT/Retro intensa, funcionando como uma **Single Page Application (SPA)** minimalista gerada estaticamente via Python.

## 🚀 Funcionalidades

- **Estética CRT Avançada:** Efeitos de scanlines animadas, flicker, vinheta, curvatura de tela e brilho (glow).
- **SPA (Single Page Application):** Navegação instantânea entre o índice e as postagens sem recarregar a página.
- **Suporte a Markdown:** Escreva seus posts usando sintaxe Markdown (negrito, links, listas, imagens, etc).
- **Responsivo:** Design adaptável para desktop e dispositivos móveis.
- **Automação Simples:** Script Python para converter arquivos de texto em postagens no banco de dados e atualizar o site.

## 📁 Estrutura de Pastas

- `/css`: Estilos do blog (`style.css`).
- `/js`: Lógica de navegação e renderização (`script.js`).
- `/fonts`: Fontes WebPlus IBM VGA e Toshiba Sat.
- `/in`: Pasta para colocar novos arquivos `.txt` de postagens.
- `index.html`: O esqueleto do blog e container de dados.
- `update_posts.py`: Script principal para atualizar o blog.
- `reset_posts.py`: Script para limpar todas as postagens.
- `posts.db`: Banco de dados SQLite onde as postagens são persistidas.

## ✍️ Como Postar

1. Crie um arquivo `.txt` dentro da pasta `/in`.
2. A **primeira linha** do arquivo será o título do post.
3. O **restante** do arquivo será o corpo do post, aceitando Markdown.
4. Execute o script de atualização:
   ```bash
   python3 update_posts.py
   ```
5. O script irá:
   - Ler o arquivo.
   - Salvar no banco de dados SQLite.
   - Converter o Markdown para HTML.
   - Atualizar o arquivo `index.html` com os novos dados.
   - Remover o arquivo da pasta `/in`.

## 🛠️ Requisitos

- Python 3.x
- Biblioteca `markdown` do Python:
  ```bash
  pip install markdown
  ```

## 🧹 Resetando o Blog

Para apagar todas as postagens do banco de dados e do `index.html`, execute:
```bash
python3 reset_posts.py
```

---
*Estética mantida com carinho por Jules.*
