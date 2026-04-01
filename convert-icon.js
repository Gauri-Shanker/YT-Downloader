const pngToIco = require('png-to-ico').default;
const fs = require('fs');

const input = fs.readFileSync('icon.png');
pngToIco(input)
    .then(buf => {
        fs.writeFileSync('icon.ico', buf);
        console.log('Icon converted successfully!');
    })
    .catch(err => {
        console.error('Error converting icon:', err);
    });
