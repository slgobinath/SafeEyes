import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ScreenshotsComponent } from './screenshots.component';

describe('ScreenshotsComponent', () => {
  let component: ScreenshotsComponent;
  let fixture: ComponentFixture<ScreenshotsComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ScreenshotsComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ScreenshotsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
