import { UtilityService } from './utility.service';
import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { NgxGalleryModule } from 'ngx-gallery';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {MatTabsModule} from '@angular/material';
import { HighlightJsModule, HighlightJsService } from 'angular2-highlight-js';
import { CollapseModule } from 'ngx-bootstrap';

import { AppComponent } from './app.component';
import { ScreenshotsComponent } from './screenshots/screenshots.component';
import { FeaturesComponent } from './features/features.component';
import { InstallationComponent } from './installation/installation.component';
import { ContributeComponent } from './contribute/contribute.component';
import { NavbarComponent } from './navbar/navbar.component';
import { HeaderComponent } from './header/header.component';

@NgModule({
  declarations: [
    AppComponent,
    ScreenshotsComponent,
    FeaturesComponent,
    InstallationComponent,
    ContributeComponent,
    NavbarComponent,
    HeaderComponent
  ],
  imports: [
    BrowserModule,
    NgxGalleryModule,
    BrowserAnimationsModule,
    MatTabsModule,
    HighlightJsModule,
    CollapseModule
  ],
  providers: [
    UtilityService,
    HighlightJsService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
