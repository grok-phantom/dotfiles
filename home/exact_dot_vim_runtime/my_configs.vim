set encoding=UTF-8
set clipboard=unnamed
colorscheme gruvbox


let g:SuperTabDefaultCompletionType = "<c-n>"

let g:ale_linters = {
\    'python': ['flake8'],
\    'cpp': ['clangtidy'],
\    'c': ['clangtidy'],
\}
let g:ale_fixers = {
\    'python': ['black'],
\    'cpp': ['clang-format'],
\    '*': ['remove_trailing_lines', 'trim_whitespace']
\}
let g:ale_python_flake8_options = '--max-line-length=88 --extend-ignore=E203'
map <F6> :ALEFix<CR>

let g:ctrlp_user_command = ['.git', 'cd %s && git ls-files -co --exclude-standard']

call pathogen#infect()

nmap <leader>c <Plug>OSCYankOperator
nmap <leader>cc <leader>c_
vmap <leader>c <Plug>OSCYankVisual
