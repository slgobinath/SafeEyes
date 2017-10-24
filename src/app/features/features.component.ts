import { UtilityService } from './../utility.service';
import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'features',
  templateUrl: './features.component.html',
  styleUrls: ['./features.component.css']
})
export class FeaturesComponent implements OnInit {

  constructor(private _utilService: UtilityService) { }

  features;

  ngOnInit() {
    let features = [
      {
        icon: 'fa-coffee',
        title: 'Breaks with exercises',
        description: 'The whole purpose of Safe Eyes is reminding you to take breaks while working on the computer for a long time. The break screen asks you to do some exercises which will reduce your RSI.'
      },
      {
        icon: 'fa-beer',
        title: 'Strict break for workaholics',
        description: '​Strict break mode prevents computer addicts from skipping breaks unconsciously. In skip break mode, the user cannot skip or postpone the break.'
      },
      {
        icon: 'fa-desktop',
        title: 'Multi-display support',
        description: 'Workstations with dual monitors are cool to have but Safe Eyes locks all at the same time to relax your eyes during the break.'
      },
      {
        icon: 'fa-bell',
        title: 'Notifications',
        description: 'Safe Eyes shows a system notification before breaks and an audible alert at the end of breaks. Even if you are few steps away from your computer, you can hear the call for back to work.'
      },
      {
        icon: 'fa-lightbulb-o',
        title: 'Smart decisions',
        description: 'If you are working with a fullscreen application, Safe Eyes will not bother you. It also can sense if your system is idle and postpone the break based on idle period.'
      },
      {
        icon: 'fa-lock',
        title: 'Lock screen',
        description: 'Some long breaks may ask you to leave the computer for a while. In such scenarios, Safe Eyes locks the computer by starting the default screensaver to prevent unauthorized access to your computer.'
      },
      {
        icon: 'fa-paint-brush',
        title: 'Sexy look and feel',
        description: 'Compared to similar products, Safe Eyes comes with a simple and sexy look and feel and also provides the ability to customize the appearance using CSS stylesheet.'
      },
      {
        icon: 'fa-puzzle-piece',
        title: 'Extensible with plug-ins',
        description: 'Plug-in support is one of the cool things Safe Eyes offers. You can customize almost everything using custom plug-ins.'
      }
      ,
      {
        icon: 'fa-cogs',
        title: 'APIs for developers',
        description: '​Safe Eyes can be controlled externally by using the Remote Procedure Call (RPC) API and command-line parameters.'
      }
    ];
    this.features = this._utilService.distribute(features, 3);
  }
}
