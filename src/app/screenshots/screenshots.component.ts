import { Component, OnInit } from '@angular/core';
import { NgxGalleryOptions, NgxGalleryImage, NgxGalleryAnimation } from 'ngx-gallery';

@Component({
  selector: 'screenshots',
  templateUrl: './screenshots.component.html',
  styleUrls: ['./screenshots.component.css']
})
export class ScreenshotsComponent implements OnInit {

  constructor() { }

  galleryOptions: NgxGalleryOptions[];
  galleryImages: NgxGalleryImage[];

  ngOnInit() {

    this.galleryOptions = [
      {
        width: '100%',
        height: '500px',
        thumbnailsColumns: 4,
        imageAnimation: NgxGalleryAnimation.Slide,
        imageAutoPlay: true,
        imageAutoPlayInterval: 2000,
        thumbnails: false
      },
      // max-width 800
      {
        breakpoint: 800,
        width: '100%',
        height: '600px',
        imagePercent: 80,
      },
      // max-width 400
      {
        breakpoint: 400,
        preview: false
      }
    ];

    this.galleryImages = [
      {
        small: 'assets/screenshots/safeeyes_1.png',
        medium: 'assets/screenshots/safeeyes_1.png',
        big: 'assets/screenshots/safeeyes_1.png'
      },
      {
        small: 'assets/screenshots/safeeyes_2.png',
        medium: 'assets/screenshots/safeeyes_2.png',
        big: 'assets/screenshots/safeeyes_2.png'
      },
      {
        small: 'assets/screenshots/safeeyes_3.png',
        medium: 'assets/screenshots/safeeyes_3.png',
        big: 'assets/screenshots/safeeyes_3.png'
      },
      {
        small: 'assets/screenshots/safeeyes_4.png',
        medium: 'assets/screenshots/safeeyes_4.png',
        big: 'assets/screenshots/safeeyes_4.png'
      },
      {
        small: 'assets/screenshots/safeeyes_5.png',
        medium: 'assets/screenshots/safeeyes_5.png',
        big: 'assets/screenshots/safeeyes_5.png'
      },
      {
        small: 'assets/screenshots/safeeyes_6.png',
        medium: 'assets/screenshots/safeeyes_6.png',
        big: 'assets/screenshots/safeeyes_6.png'
      }
    ];
  }
}
