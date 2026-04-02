document.getElementById('uploadBtn').addEventListener('click', async () => {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) {
        alert('Выберите файл');
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    document.getElementById('result').innerHTML = 'Обработка...';
    document.getElementById('imageResult').innerHTML = '';

    try {
        const response = await fetch('/upload', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.error) {
            document.getElementById('result').innerHTML = `<span style="color:red;">Ошибка: ${data.error}</span>`;
        } else {
            let resultText = `Количество гостей: ${data.guest_count}`;
            if (data.num_tables !== undefined) resultText += `<br>Количество столов: ${data.num_tables}`;
            resultText += `<br>Загруженность: ${data.occupancy}`;
            document.getElementById('result').innerHTML = resultText;
            if (data.annotated_image) {
                const img = new Image();
                img.onload = () => {
                    document.getElementById('imageResult').innerHTML = '';
                    document.getElementById('imageResult').appendChild(img);
                };
                img.onerror = () => {
                    console.error('Не удалось загрузить изображение:', data.annotated_image);
                    document.getElementById('imageResult').innerHTML = '<span style="color:red;">Не удалось отобразить аннотированное изображение</span>';
                };
                img.src = data.annotated_image;
                img.style.maxWidth = '100%';
                img.style.maxHeight = '400px';
                img.style.border = '1px solid #ccc';
            } else if (data.is_video) {
                document.getElementById('imageResult').innerHTML = `<p>${data.message}</p>`;
            }
        }
    } catch (err) {
        console.error(err);
        document.getElementById('result').innerHTML = '<span style="color:red;">Ошибка при отправке файла</span>';
    }
    loadHistory();
});

const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const snapshotBtn = document.getElementById('snapshotBtn');

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => { video.srcObject = stream; })
        .catch(err => console.error("Ошибка доступа к камере:", err));
}

snapshotBtn.addEventListener('click', async () => {
    if (!video.videoWidth) {
        alert('Камера не активна');
        return;
    }
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg');
    document.getElementById('result').innerHTML = 'Обработка...';
    document.getElementById('imageResult').innerHTML = '';
    try {
        const response = await fetch('/camera', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        const data = await response.json();
        if (data.error) {
            document.getElementById('result').innerHTML = `<span style="color:red;">Ошибка: ${data.error}</span>`;
        } else {
            let resultText = `Количество гостей: ${data.guest_count}`;
            if (data.num_tables !== undefined) resultText += `<br>Количество столов: ${data.num_tables}`;
            resultText += `<br>Загруженность: ${data.occupancy}`;
            document.getElementById('result').innerHTML = resultText;
            if (data.annotated_image) {
                const img = new Image();
                img.onload = () => {
                    document.getElementById('imageResult').innerHTML = '';
                    document.getElementById('imageResult').appendChild(img);
                };
                img.onerror = () => {
                    console.error('Не удалось загрузить изображение:', data.annotated_image);
                    document.getElementById('imageResult').innerHTML = '<span style="color:red;">Ошибка отображения фото</span>';
                };
                img.src = data.annotated_image;
                img.style.maxWidth = '100%';
                img.style.maxHeight = '400px';
                img.style.border = '1px solid #ccc';
            }
        }
    } catch (err) {
        console.error(err);
        document.getElementById('result').innerHTML = '<span style="color:red;">Ошибка при отправке снимка</span>';
    }
    loadHistory();
});

async function loadHistory() {
    try {
        const response = await fetch('/history');
        const history = await response.json();
        const historyDiv = document.getElementById('historyList');
        if (history.length === 0) {
            historyDiv.innerHTML = '<p>История пуста</p>';
            return;
        }
        historyDiv.innerHTML = '<h3>Последние записи</h3><ul>' +
            history.slice().reverse().slice(0, 20).map(rec =>
                `<li>${new Date(rec.timestamp).toLocaleString()} — ${rec.image_name} — 👥 ${rec.guest_count} гостей — Загруженность: ${rec.occupancy}</li>`
            ).join('') + '</ul>';
    } catch (err) {
        console.error('Ошибка загрузки истории:', err);
        document.getElementById('historyList').innerHTML = '<p style="color:red;">Ошибка загрузки истории</p>';
    }
}

document.getElementById('refreshHistoryBtn').addEventListener('click', loadHistory);
document.getElementById('reportPdfBtn').addEventListener('click', () => window.open('/report/pdf', '_blank'));
document.getElementById('reportExcelBtn').addEventListener('click', () => window.open('/report/excel', '_blank'));

loadHistory();
