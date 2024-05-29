let selectedRewards = [];

function updateQuantity(rewardId, action) {
    let quantitySpan = document.getElementById('quantity-' + rewardId);
    let quantity = parseInt(quantitySpan.textContent);
    let rewardIndex = selectedRewards.findIndex(r => r.reward_id === rewardId);

    if (action === 'buy') {
        quantity += 1;
    } else if (action === 'sell' && quantity > 0) {
        quantity -= 1;
    }

    quantitySpan.textContent = quantity;

    if (rewardIndex !== -1) {
        selectedRewards[rewardIndex].quantity = quantity;
        if (quantity === 0) {
            selectedRewards.splice(rewardIndex, 1);
        }
    } else if (quantity > 0) {
        selectedRewards.push({
            reward_id: rewardId,
            title: document.querySelector(`#quantity-${rewardId}`).closest('.reward-item').querySelector('h4').textContent,
            quantity: quantity,
            points: parseInt(document.querySelector(`#quantity-${rewardId}`).closest('.reward-item').querySelector('p').textContent)
        });
    }

    updateReceipt();
}

function updateReceipt() {
    let receipt = document.getElementById('receipt');
    receipt.innerHTML = '';
    selectedRewards.forEach(reward => {
        let li = document.createElement('li');
        li.textContent = `${reward.title}: ${reward.quantity} x ${reward.points} points`;
        receipt.appendChild(li);
    });
}

function completeTransaction() {
    let form = document.getElementById('redeem-form');
    document.getElementById('selected_rewards').value = JSON.stringify(selectedRewards);
    form.submit();
}

function cancelTransaction() {
    fetch("{% url 'shop_cancel_transaction' %}", {method: 'POST', headers: {'X-CSRFToken': '{{ csrf_token }}'}})
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                window.location.href = "{% url 'shop_home' %}";
            }
        });
}
