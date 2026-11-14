/**
 * Helper for parsing xmfa files
 *
 */

const xmfaParser  = require('./xmfa-parser');
const fs = require('fs');
const util = require('util');
const opts = require('commander');

const readFile = util.promisify(fs.readFile);


if (require.main === module) {
    opts.option('-i, --input [value]', 'Path to .xmfa')
      .parse(process.argv)

    main(opts);
}


async function main(opts) {
    try {
        let data = await parser(opts.input, false, true);
        console.log(JSON.stringify(data, null, 4));
    } catch(e) {
        console.error(e.message);
    }
}

async function parser(path, includeSeqs, includeGaps) {
    let data = await readFile(path, 'utf-8');

    // use parser
    let lcbs = xmfaParser.parse(data);

    if (includeGaps) {
        for (let i=0; i < lcbs.length; i++) {
            let regions = lcbs[i];
            for (let j=0; j < regions.length; j++ ) {
                let region = regions[j];
                region.gaps = getGaps(region.seq);
            }
        }
    }

    // only includes sequences if requested, remove paths (for now)
    if (!includeSeqs) {
        for (let i=0; i < lcbs.length; i++) {
            let lcb = lcbs[i];
            for (let j=0; j < lcb.length; j++ ) {
                let region = lcb[j];
                let name = region.name;
                region.name = name.substr(name.lastIndexOf('/') + 1);
                delete region.seq;
            }
        }
    }

    return lcbs;
}

function getGaps(sequence) {
    let gaps = []
    let start, end;
    for (let i = 1; i <= sequence.length; i++) {
        let nt = sequence.charAt(i-1);

        if (!['a','t', 'g', 'c', '-', 'n'].includes(nt.toLowerCase()) ) {
            console.error(`invalid char "${nt}" in sequence.`)
        }

        if (!start && nt === '-') start = i;

        if (start && nt !== '-') {
            end = i;
            gaps.push({start, end});
            start = null;
        }
    }

    return gaps;
}

module.exports = parser;