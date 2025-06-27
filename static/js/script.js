document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('dietForm');
  const resultDiv = document.getElementById('result');

  if (form) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();

      const formData = new FormData(form);
      const data = {
        age: parseInt(formData.get('age')),
        gender: formData.get('gender'),
        goal: formData.get('goal'),
        condition: formData.get('condition'),
      };

      try {
        const res = await fetch('/predict_diet', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });

        const result = await res.json();
        resultDiv.innerHTML = `<p class="text-xl font-semibold mt-4 text-green-700">Diet Plan: ${result.prediction}</p>`;
      } catch (err) {
        console.error(err);
        resultDiv.innerHTML = `<p class="text-red-600">Error: Unable to get prediction.</p>`;
      }
    });
  }
});
