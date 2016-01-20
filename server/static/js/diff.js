$("table.diff").each(function(i, table) {
    var lineNums = $(table).find('td.diff-linenum'),
        lineCode = $(table).find('pre code'),
        leftNums = [], rightNums = [];

    for (var j = 0; j < lineNums.length; j++) {
        ((j % 2 == 0) ? leftNums : rightNums).push(lineNums[j].innerText);
    }

    var nums, line, result, state;
    for (var k = 0; k < 2; k++) {
        nums = (k % 2) ? leftNums : rightNums;
        for (j = 0; j < nums.length; j++) {
            if (nums[j] !== "") {
                line = lineCode[j];
                // TODO: infer language by filetype
                result = hljs.highlight("python", $(line).text(), true, state);
                state = result.top;
                $(line).html(result.value);
            }
        }
    }
});
