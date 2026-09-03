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
function moveDate(date, amount) { const d = new Date(date); d.setDate(d.getDate() + amount); return d; }
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
let selected = todayInKorea();
if (!isWeekday(selected)) selected = moveWeekday(selected, selected.getDay() === 0 ? -1 : 1);

function render() {
  const key = toKey(selected);
  const meal = meals[key];
  $('dateLabel').textContent = displayDate(selected);
  $('dayLabel').textContent = displayDate(selected);
  $('mealCard').classList.remove('loading');
  $('menuList').innerHTML = '';
  $('emptyMessage').classList.toggle('hidden', !!meal);
  $('mealTitle').textContent = meal ? '오늘의 급식' : '급식 정보가 없습니다';
  $('kcal').textContent = meal?.kcal ? `${meal.kcal} kcal` : '';
  if (meal) {
    (meal.menu || []).forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      $('menuList').appendChild(li);
    });
  }
  renderWeek();
}

function renderWeek() {
  const root = $('weekList');
  root.innerHTML = '';

  // 선택한 날짜가 속한 주를 기준으로 주 급식을 표시한다.
  // 따라서 다음 주 월요일로 넘어가면 '이번 주 급식'도 다음 주로 함께 이동한다.
  const monday = getMonday(selected);
  const sunday = moveDate(monday, 6);
  const mondayKey = toKey(monday);
  const sundayKey = toKey(sunday);
  const todayKey = toKey(todayInKorea());
  $('weekLabel').textContent = `${monday.getMonth() + 1}/${monday.getDate()}–${sunday.getMonth() + 1}/${sunday.getDate()}`;

  for (let i = 0; i < 5; i++) {
    const d = moveDate(monday, i);
    const key = toKey(d);
    const meal = meals[key];
    const item = document.createElement('button');
    item.className = `week-item ${key === toKey(selected) ? 'active' : ''}`;

    const date = document.createElement('span');
    date.className = 'week-date';
    date.textContent = `${d.getMonth() + 1}/${d.getDate()} ${d.toLocaleDateString('ko-KR', { weekday: 'short' })}`;

    const menu = document.createElement('span');
    menu.className = 'week-menu';
    menu.textContent = meal ? (meal.menu || []).join(' · ') : '급식 정보 없음';

    item.append(date, menu);
    item.onclick = () => { selected = d; render(); };
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
  .then(response => { if (!response.ok) throw new Error('데이터 요청 실패'); return response.json(); })
  .then(data => {
    meals = data.meals || {};
    $('updatedAt').textContent = data.updatedAt ? `데이터 업데이트: ${data.updatedAt}` : '';
    render();
  })
  .catch(() => {
    $('mealCard').classList.remove('loading');
    $('mealTitle').textContent = '급식 데이터를 불러오지 못했습니다';
    $('emptyMessage').classList.add('hidden');
  });
