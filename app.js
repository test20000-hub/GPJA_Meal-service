const DATA_URL = `./data/meals.json?t=${Date.now()}`;
const dateFmt = new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' });
const isoFmt = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul' });
let meals = {};

const $ = (id) => document.getElementById(id);

function toKey(date) {
  return isoFmt.format(date);
}

function todayInKorea() {
  const key = toKey(new Date());
  const [year, month, day] = key.split('-').map(Number);
  return new Date(year, month - 1, day);
}

function displayDate(date) {
  return dateFmt.format(date);
}

function moveDate(date, amount) {
  const d = new Date(date);
  d.setDate(d.getDate() + amount);
  return d;
}

function startOfWeek(date) {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

function endOfWeek(date) {
  return moveDate(startOfWeek(date), 6);
}

let selected = todayInKorea();

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
  const start = startOfWeek(selected);
  const end = endOfWeek(selected);
  $('weekLabel').textContent = `${start.toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' })} ~ ${end.toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' })}`;

  const root = $('weekList');
  root.innerHTML = '';

  for (let i = 0; i < 7; i++) {
    const d = moveDate(start, i);
    const key = toKey(d);
    const meal = meals[key];
    const item = document.createElement('button');
    item.className = `week-item ${key === toKey(selected) ? 'active' : ''}`;

    const date = document.createElement('span');
    date.className = 'week-date';
    date.textContent = `${d.getMonth() + 1}/${d.getDate()} ${d.toLocaleDateString('ko-KR', { weekday: 'short' })}`;

    const menu = document.createElement('span');
    menu.className = 'week-menu';
    menu.textContent = meal ? (meal.menu || []).join(' · ') : '급식 없음';

    item.append(date, menu);
    item.onclick = () => {
      selected = d;
      render();
    };
    root.appendChild(item);
  }
}

$('prevBtn').onclick = () => {
  selected = moveDate(selected, -1);
  render();
};

$('nextBtn').onclick = () => {
  selected = moveDate(selected, 1);
  render();
};

$('todayBtn').onclick = () => {
  selected = todayInKorea();
  render();
};

fetch(DATA_URL, { cache: 'no-store' })
  .then(response => {
    if (!response.ok) throw new Error('데이터 요청 실패');
    return response.json();
  })
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
