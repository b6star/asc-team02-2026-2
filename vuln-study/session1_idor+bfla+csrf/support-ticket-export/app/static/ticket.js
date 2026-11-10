const ticketDetail = document.querySelector('#ticket-detail');
const ticketTitle = document.querySelector('#ticket-title');
const ticketEyebrow = document.querySelector('#ticket-eyebrow');
const ticketLead = document.querySelector('#ticket-lead');
const ticketReference = ticketDetail.dataset.ticketReference;
const ticketCode = new URLSearchParams(location.search).get('code');

async function loadTicket() {
  try {
    const codeQuery = ticketCode ? `?code=${encodeURIComponent(ticketCode)}` : '';
    const response = await fetch(`/api/tickets/${encodeURIComponent(ticketReference)}${codeQuery}`);
    const ticket = await response.json();
    if (!response.ok) throw new Error(ticket.error || '문의 정보를 불러오지 못했습니다.');

    const internal = ticket.classification === '내부';
    ticketTitle.textContent = ticket.title;
    ticketDetail.className = internal ? 'detail-box internal-ticket' : 'detail-box';
    ticketDetail.replaceChildren();
    if (internal) {
      ticketEyebrow.textContent = 'INTERNAL TICKET';
      ticketLead.textContent = '사내 구성원 간에 등록된 업무 요청과 처리 내용을 확인합니다.';
      const badge = document.createElement('span');
      badge.className = 'internal-badge';
      badge.textContent = 'INTERNAL · 사내 업무';
      ticketDetail.append(badge);
    }
    const details = document.createElement('dl');
    details.className = 'detail-grid';
    const rows = [
      [internal ? '티켓 번호' : '문의 번호', `#${ticket.ticketNumber}`],
      ['상태', ticket.status],
      [internal ? '작성자' : '문의 작성자', ticket.openedBy],
      [internal ? '작성 시간' : '접수 시간', ticket.openedAt],
      ['담당자', ticket.claimedBy],
      [internal ? '업무 내용' : '문의 내용', ticket.reason],
      ['첨부파일', ticket.attachmentFilename || '없음'],
    ];
    for (const [label, value] of rows) {
      const term = document.createElement('dt');
      const description = document.createElement('dd');
      term.textContent = label;
      description.textContent = value;
      if (label === '업무 내용' || label === '문의 내용') description.className = 'ticket-body';
      details.append(term, description);
    }
    if (ticket.status === '처리 완료') {
      const answerTerm = document.createElement('dt');
      const answerDescription = document.createElement('dd');
      answerTerm.textContent = internal ? '담당자 답변' : '답변';
      answerDescription.textContent = ticket.answer || '등록된 답변이 없습니다.';
      answerDescription.className = 'ticket-answer';
      details.append(answerTerm, answerDescription);
    }
    ticketDetail.append(details);

    if (ticket.attachmentId) {
      const previewTypes = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp']);
      if (!internal && previewTypes.has(ticket.attachmentContentType)) {
        const preview = document.createElement('img');
        preview.className = 'attachment-preview';
        preview.src = `/api/attachments/${ticket.attachmentId}?preview=1`;
        preview.alt = `${ticket.attachmentFilename} 미리보기`;
        ticketDetail.append(preview);
      }
      const download = document.createElement('a');
      download.className = 'file-link';
      download.href = `/api/attachments/${ticket.attachmentId}`;
      download.textContent = '첨부파일 받기 →';
      ticketDetail.append(download);
    }

    if (ticket.canReplaceAttachment) addReplaceForm(ticket);
  } catch (error) {
    ticketTitle.textContent = '문의를 찾을 수 없습니다.';
    ticketDetail.className = 'detail-box error';
    ticketDetail.textContent = error.message;
  }
}

function addReplaceForm(ticket) {
  const form = document.createElement('form');
  form.className = 'replace-form';
  const label = document.createElement('label');
  label.textContent = '첨부 이미지 교체 (PNG, JPG, GIF, WEBP, SVG)';
  const input = document.createElement('input');
  input.type = 'file';
  input.name = 'file';
  input.accept = '.png,.jpg,.jpeg,.gif,.webp,.svg,image/png,image/jpeg,image/gif,image/webp,image/svg+xml';
  input.required = true;
  const button = document.createElement('button');
  button.className = 'primary';
  button.type = 'submit';
  button.textContent = '첨부파일 교체';
  const result = document.createElement('div');
  result.className = 'result-message';
  label.append(input);
  form.append(label, button, result);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    result.className = 'result-message';
    result.textContent = '첨부파일을 교체하는 중입니다.';
    try {
      const response = await fetch(`/api/tickets/${encodeURIComponent(ticket.id)}/attachment`, {
        method: 'POST',
        body: new FormData(form),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || '첨부파일을 교체하지 못했습니다.');
      result.className = 'result-message success';
      result.textContent = '첨부 이미지가 교체되었습니다.';
      setTimeout(() => location.reload(), 800);
    } catch (error) {
      result.className = 'result-message error';
      result.textContent = error.message;
    }
  });
  ticketDetail.append(form);
}

loadTicket();
