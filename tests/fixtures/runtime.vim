set nomodeline noswapfile noundofile virtualedit=onemore
setlocal buftype=nofile bufhidden=wipe
call assert_equal(1, has('python3'), 'Python 3 loadable')
call assert_equal(2, exists(':TagbarToggle'), 'Tagbar loaded')
call assert_equal(2, exists(':ALEInfo'), 'ALE loaded')
call assert_equal(1, exists('*fzf#wrap'), 'fzf main runtime loaded')
call assert_equal("needle\n", system('printf "needle\nother\n" | fzf --filter=needle'), 'fzf executable filter')
setfiletype python
call assert_equal(1, jedi#init_python(), 'Jedi initialized')
call assert_equal('jedi#completions', &l:omnifunc, 'Python omnifunc')
call setline(1, ['value = "hello"', 'value.'])
call cursor(2, 7)
let s:result = jedi#completions(0, '')
let s:words = type(s:result) == v:t_dict ? s:result.words : s:result
call assert_true(index(map(copy(s:words), 'v:val.word'), 'upper') >= 0, 'String completion')
python3 << PY
import vim, jedi_vim
vim.current.buffer[:] = ['from pathlib import Path', 'Path(".").']
assert 'exists' in [item.name for item in jedi_vim.get_script().complete(2, 10)]
vim.current.buffer[:] = ['def greet(name: str) -> str:', '    return "hello " + name', 'greet(']
script = jedi_vim.get_script()
assert script.get_signatures(3, 6)[0].params[0].name == 'name'
assert script.goto(3, 3)[0].line == 1
PY
if !empty(v:errors)
  call writefile(v:errors, $VIM_SMOKE_RESULT)
  cquit 1
endif
call writefile(['PASS'], $VIM_SMOKE_RESULT)
qa!
