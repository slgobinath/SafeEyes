import { UtilityService } from './../utility.service';
import { Component, OnInit } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';

@Component({
  selector: 'contribute',
  templateUrl: './contribute.component.html',
  styleUrls: ['./contribute.component.css']
})
export class ContributeComponent implements OnInit {

  constructor(private _utilService: UtilityService, private _sanitizer: DomSanitizer) { }
  
    contributions;
  
    ngOnInit() {
      let contributions = [
        {
          icon: 'fa-globe',
          title: 'Translate Safe Eyes',
          description: this._sanitizer.bypassSecurityTrustHtml('Safe Eyes is localized using Weblate, please visit the Weblate hosted <a href="https://hosted.weblate.org/projects/safe-eyes/translations/">Safe Eyes translations</a> site in order to assist with translations. Please translate the message id <i>description</i> as a meaningful description describing Safe Eyes.')
        },
        {
          icon: 'fa-github',
          title: 'Issues',
          description: 'If you are having issues with Safe Eyes, feel free to open issues in the <a href="https://github.com/slgobinath/SafeEyes/issues">Safe Eyes Github Issues</a> page as necessary.'
        }
      ];
      this.contributions = this._utilService.distribute(contributions, 2);
    }

}
