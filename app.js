const DATA_URL = `./data/meals.json?t=${Date.now()}`;
const dateFmt = new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' });
const isoFmt = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul' });
let meals = {};

const $ = (id) => document.getElementById(id);
function toKey(date) { return isoFmt.format(date); }
function todayInKorea() {
  const key = toKey(new Date());
  const [year, month, day] = key.split('-').map(Number);
  return new Date(year, month - 1, day);
}
function displayDate(date) { return dateFmt.format(date); }
function moveDate(date, amount) {
  const d = new Date(date);
  d.setDate(d.getDate() + amount);
  return d;
}
function isWeekday(date) { return date.getDay() !== 0 && date.getDay() !== 6; }
function moveWeekday(date, direction) {
  let d = moveDate(date, direction);
  while (!isWeekday(d)) d = moveDate(d, direction > 0 ? 1 : -1);
  return d;
}
function getMonday(date) {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - (day === 0 ? 6 : day - 1));
  return d;
}
function formatKcal(value) {
  if (value === undefined || value === null || value === '') return '';
  return `${Number(value).toLocaleString('ko-KR', { maximumFractionDigits: 1 })} kcal`;
}

let selected = todayInKorea();
if (!isWeekday(selected)) selected = moveWeekday(selected, selected.getDay() === 0 ? -1 : 1);

function render() {
  const key = toKey(selected);
  const meal = meals[key];
  const card = $('mealCard');

  $('dateLabel').textContent = displayDate(selected);
  $('dayLabel').textContent = displayDate(selected);
  $('kcal').textContent = meal ? formatKcal(meal.kcal) : '';
  card.classList.remove('loading');
  card.classList.remove('is-changing');
  void card.offsetWidth;
  card.classList.add('is-changing');

  $('menuList').innerHTML = '';
  $('emptyMessage').classList.toggle('hidden', !!meal);
  $('mealTitle').textContent = meal ? '오늘의 급식' : '급식 정보가 없습니다';

  if (meal) {
    (meal.menu || []).forEach((item, index) => {
      const li = document.createElement('li');
      li.style.setProperty('--item-index', index);
      li.textContent = item;
      $('menuList').appendChild(li);
    });
  }
  renderWeek();
}

function renderWeek() {
  const root = $('weekList');
  root.innerHTML = '';
  const monday = getMonday(selected);
  const friday = moveDate(monday, 4);
  $('weekLabel').textContent = `${monday.getMonth() + 1}/${monday.getDate()}–${friday.getMonth() + 1}/${friday.getDate()}`;

  const selectedKey = toKey(selected);
  for (let i = 0; i < 5; i++) {
    const d = moveDate(monday, i);
    const key = toKey(d);
    const meal = meals[key];
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `week-item ${key === selectedKey ? 'active' : ''}`;
    item.setAttribute('aria-label', `${displayDate(d)} 급식 보기`);

    const date = document.createElement('span');
    date.className = 'week-date';
    date.textContent = `${d.getMonth() + 1}/${d.getDate()} ${d.toLocaleDateString('ko-KR', { weekday: 'short' })}`;

    const menu = document.createElement('span');
    menu.className = 'week-menu';
    menu.textContent = meal ? (meal.menu || []).join(' · ') : '급식 정보 없음';

    item.append(date, menu);
    item.onclick = () => {
      selected = d;
      render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };
    root.appendChild(item);
  }
}

$('prevBtn').onclick = () => { selected = moveWeekday(selected, -1); render(); };
$('nextBtn').onclick = () => { selected = moveWeekday(selected, 1); render(); };
$('todayBtn').onclick = () => {
  selected = todayInKorea();
  if (!isWeekday(selected)) selected = moveWeekday(selected, selected.getDay() === 0 ? -1 : 1);
  render();
};

fetch(DATA_URL, { cache: 'no-store' })
  .then(response => {
    if (!response.ok) throw new Error('데이터 요청 실패');
    return response.json();
  })
  .then(data => {
    meals = data.meals || {};
    $('updatedAt').textContent = data.updatedAt ? `데이터 업데이트 · ${data.updatedAt}` : '';
    render();
  })
  .catch(() => {
    $('mealCard').classList.remove('loading');
    $('mealTitle').textContent = '급식 데이터를 불러오지 못했습니다';
    $('emptyMessage').classList.add('hidden');
    $('kcal').textContent = '';
  });
