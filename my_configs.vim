colorscheme gruvbox

set encoding=UTF-8
set clipboard=unnamed
set shiftwidth=2
set tabstop=2

"" YCM
"let g:ycm_global_ycm_extra_conf = '~/.vim_runtime/my_plugins/YouCompleteMe/.ycm_extra_conf.py'
"let g:ycm_python_binary_path = 'python'
"let g:ycm_confirm_extra_conf = 0
"let g:ycm_key_list_select_completion = ['<C-n>', '<Down>']
"let g:ycm_key_list_previous_completion = ['<C-p>', '<Up>']

" Supertab setting
let g:SuperTabDefaultCompletionType = '<C-n>'

" UltiSnips setting
" make vim recognizing snippets dir
set runtimepath+=~/.vim/my-snippets/
" use different snippets dir
let g:UltiSnipsSnippetsDir='~/.vim/my-snippets/'
let g:UltiSnipsSnippetDirectories=["my-snippets"]
" better key bindings for UltiSnipsExpandTrigger
let g:UltiSnipsExpandTrigger = "<tab>"
let g:UltiSnipsJumpForwardTrigger = "<tab>"
let g:UltiSnipsJumpBackwardTrigger = "<s-tab>"

" latex section
let g:vimtex_view_method='skim'
let g:vimtex_view_general_options = '--unique file:@pdf\#src:@line@tex'
let g:vimtex_view_general_options_latexmk = '--unique'
let g:vimtex_quickfix_mode = 0
set conceallevel=2
let g:tex_conceal="abdgms"

" Autopep8 section
let g:autopep8_indent_size=2
let g:autopep8_disable_show_diff=1
let g:autopep8_on_save=1
autocmd FileType python noremap <buffer> <F8> :call Autopep8()<CR>
" General section
autocmd Filetype python setlocal ts=2 sw=2 expandtab
" Clang-format section
autocmd FileType c,cpp noremap <buffer> <F8> :w<CR> :ClangFormat<CR>
