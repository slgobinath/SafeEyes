import { Injectable } from '@angular/core';

@Injectable()
export class UtilityService {

  constructor() { }

  distribute(array, columns) {
    if (array.length <= columns) {
      return [array];
    };

    let rowsNum = Math.ceil(array.length / columns);

    let rowsArray = new Array(rowsNum);

    for (let i = 0; i < rowsNum; i++) {
      let columnsArray = new Array(columns);
      for (let j = 0; j < columns; j++) {
        let index = i * columns + j;

        if (index < array.length) {
          columnsArray[j] = array[index];
        } else {
          break;
        }
      }
      rowsArray[i] = columnsArray;
    }
    return rowsArray;
  }

}
