// раскрытие пунктов дерева + «показать в договоре» (скролл + подсветка)
document.addEventListener('click', function (e) {
  const t = e.target.closest('.show');
  if (!t) return;
  e.preventDefault();
  const id = t.getAttribute('data-target');
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add('flash');
  setTimeout(() => el.classList.remove('flash'), 1600);
});

// индикатор «идёт анализ…» при сабмите формы
document.addEventListener('submit', function () {
  const s = document.querySelector('.spin');
  if (s) s.style.display = 'inline-flex';
});
