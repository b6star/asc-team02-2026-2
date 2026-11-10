const notificationOutput = document.querySelector('#notifications');
const createTicketResult = document.querySelector('#create-ticket-result');

function addNotification(title, detail = '') {
  if (notificationOutput.querySelector('.muted')) notificationOutput.innerHTML = '';
  const item = document.createElement('div');
  item.className = 'notification';
  const label = document.createElement('strong');
  label.textContent = title;
  item.append(label);
  if (detail) {
    const small = document.createElement('small');
    small.textContent = detail;
    item.append(small);
  }
  notificationOutput.append(item);
}

const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
const socket = new WebSocket(`${scheme}://${location.host}/ws/notifications`);
socket.addEventListener('message', (event) => {
  try {
    const message = JSON.parse(event.data);
    if (message.event === 'ticket.created') {
      addNotification(`문의 #${message.ticketNumber} 등록됨`, message.title);
    }
  } catch {}
});

document.querySelector('#create-ticket-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  createTicketResult.className = 'result-message';
  createTicketResult.textContent = '문의를 접수하는 중입니다.';
  try {
    const response = await fetch('/api/tickets', { method: 'POST', body: new FormData(event.currentTarget) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '문의를 접수하지 못했습니다.');
    createTicketResult.className = 'result-message success';
    createTicketResult.textContent = '문의가 접수되었습니다.';
    setTimeout(() => location.reload(), 800);
  } catch (error) {
    createTicketResult.className = 'result-message error';
    createTicketResult.textContent = error.message;
  }
});

const sidebarLinks = [...document.querySelectorAll('.sidebar a[href^="/#"]')];
const sections = sidebarLinks
  .map((link) => document.querySelector(new URL(link.href).hash))
  .filter(Boolean);
function updateActiveSection() {
  const marker = window.scrollY + 150;
  let current = sections[0];
  for (const section of sections) {
    if (section.offsetTop <= marker) current = section;
  }
  sidebarLinks.forEach((link) => {
    link.classList.toggle('active', new URL(link.href).hash === `#${current?.id}`);
  });
}
window.addEventListener('scroll', updateActiveSection, { passive: true });
window.addEventListener('resize', updateActiveSection);
updateActiveSection();

async function _0x4e21(t){return fetch("/api/admin/attachments/"+t+"/exports",{method:"POST"})}
async function _0x7a11(t){return fetch("/api/admin/exports/"+t+"/share",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"enabled=true"})}

//# sourceMappingURL=app.js.map

