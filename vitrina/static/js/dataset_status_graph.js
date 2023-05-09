$(function () {
    let ctx = document.getElementById("chart").getContext("2d");
    const data = {{data|safe}};
    console.log(data)
    var chart = new Chart(ctx, {
        type: 'line',
        data: {
        },
        options: {
            responsive: true,
            title: {
                display: true,
                text: ['Duomenų rinkinių kiekis laike']
            },
            scales: {
                yAxis: {
                    display: true,
                    text: 'Duomenų rinkiniai'
                },
                xAxis: {
                    display: true,
                    type: 'time',
                    text: 'Laikas'
                }
            },
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: 'rgb(255, 99, 132)'
                    }
                }
            }
        },
        plugins: []
    })
})