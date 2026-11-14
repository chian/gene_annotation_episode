/*
 * Modified from:
 *
 * biojs-io-xmfa
 * https://github.com/erasche/biojs-io-xmfa
 *
 * Copyright (c) 2015 erasche
 * Licensed under the Apache 2 license.
 *
 * Modified to:
 *  - fix bug where lcbs aren't reported if a single lcb has sequence of length 0
 *  - not depend on biojs-io-parser
 *  - include sequence description (name)
 */

/**
@class biojsioxmfa
 */
var XmfaReader = function(text) {
  if (this.constructor !== XmfaReader) {
    return new XmfaReader(text);
  }
  this.seqCount = 0;
  this.currentSeq = {};
  this.lcbs = [];
  this.lcb = [];
  if (text !== undefined) {
    this.parse(text);
  }
  return this;
};

module.exports = XmfaReader;

XmfaReader.prototype.parse = function(text) {
  text.split('\n').forEach(function(el) {
    this.parseLine(el);
  }.bind(this));
  return this.lcbs;
};

XmfaReader.parse = function(text) {
  return (new XmfaReader()).parse(text);
};

XmfaReader.prototype.parseLine = function(line) {
  var c = line.charAt(0);
  if (line.length === 0 || c === '='){
    // end of an lcb, push and reset
    this.lcb.push(this.currentSeq);
    if(Object.keys(this.currentSeq).length !== 0){
      this.lcbs.push(this.lcb);
    }

    // Don't let LCB data persist
    this.lcb = [];
    // Don't let sequences persist beyond the end of an LCB
    this.currentSeq = {};
  }
  else if (c === '#') {
    if(line.indexOf('#Sequence') !== -1 && line.indexOf('Format\t') !== -1){
      // Count number of sequences we expect to see in LCBs
      this.seqCount += 1;
    }
  }
  else if (c === '>') {
    // push any previous sequences we have
    if(Object.keys(this.currentSeq).length !== 0){
      if(this.currentSeq.start !== 0 && this.currentSeq.end !== 0){
        this.lcb.push(this.currentSeq);
      }
    }
    var linedata0 = line.split(' ');
    var linedata1 = linedata0[1].split(':');
    var linedata2 = linedata1[1].split('-');

    // Store metadata about the current block of the lcb
    this.currentSeq = {
      'name': linedata0[3],
      'start': parseInt(linedata2[0]),
      'end': parseInt(linedata2[1]),
      'strand': linedata0[2],
      'lcb_idx': parseInt(linedata1[0]),
      'seq': ''
    };
    // Reset just in case
  } else {
    this.currentSeq.seq += line.replace(/\n/g, '');
  }
};