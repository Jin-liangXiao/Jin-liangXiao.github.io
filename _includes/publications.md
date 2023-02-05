<style>
.biblist { }

/* The item */
.biblist li { }

/* You can define custom styles for plstyle field here. */


/*************************************
   The box that contain BibTeX code
 *************************************/
div.noshow { display: none; }
div.BibTeX {
  margin-right: 1%;
  margin-left: 3%;
  margin-top: 1.2em;
  margin-bottom: 1.3em;
  border: 1px solid silver;
  padding: 0.3em 0.5em;
  background: #eeeeee;
}
div.BibTeX pre { font-size: 85%; overflow: auto;  width: 100%; }
</style>

<script>
function toggleBibtex(articleid) {
  var bib = document.getElementById('bib_'+articleid);
  if (bib) {
    if(bib.className.indexOf('BibTeX') != -1) {
    bib.className.indexOf('noshow') == -1?bib.className = 'BibTeX noshow':bib.className = 'BibTeX';
    }
  } else {
    return;
  }
}
</script>

<h2 id="publications" style="margin: 2px 0px -15px;">Publications <temp style="font-size:15px;">[</temp><a href="https://scholar.google.com.hk/citations?user=g5xlNmkAAAAJ&hl=zh-CN&oi=sra" target="_blank" style="font-size:15px;">Google Scholar</a><temp style="font-size:15px;">]</temp><temp style="font-size:15px;">[</temp><a href="https://dblp.org/pid/318/0717.html" target="_blank" style="font-size:15px;">DBLP</a><temp style="font-size:15px;">]</temp></h2>

<div class="publications">
<ol class="bibliography">

<li>
<div class="pub-row">
  <div class="col-sm-3 abbr" style="position: relative;padding-right: 15px;padding-left: 15px;">
    <img src="assets/img/cdif3.png" width="200px" class="teaser img-fluid z-depth-1" style="width=100;height=30%">
            <abbr class="badge">TGRS</abbr>
  </div>
  <div class="col-sm-9" style="position: relative;padding-right: 15px;padding-left: 20px;">
      <div class="title"><a href="https://ieeexplore.ieee.org/document/9721243">A New Context-Aware Details Injection Fidelity with Adaptive Coefficients Estimation for Variational Pansharpening</a></div>
      <div class="author"><strong>Jin-Liang Xiao</strong>, Ting-Zhu Huang*, Liang-Jian Deng*, Zhong-Cheng Wu, and Gemine Vivone</div>
      <div class="periodical"><em>IEEE Transactions on Geoscience and Remote Sensing, 2022.</em>
      </div>
    <div class="links">
      <a href="https://ieeexplore.ieee.org/document/9721243" class="btn btn-sm z-depth-0" role="button" target="_blank" style="font-size:12px;">PDF</a>
      <a href="https://github.com/liangjiandeng/CDIF" class="btn btn-sm z-depth-0" role="button" target="_blank" style="font-size:12px;">Code</a>
      <a href="" style="font-size:12px;">Project Page</a>
&nbsp;<a href="javascript:toggleBibtex('xiaotgrs2022')" class="btn btn-sm z-depth-0" role="button" target="_blank" style="font-size:12px;">[BibTeX]</a>
<div id="bib_xiaotgrs2022" class="BibTeX noshow">
<pre>
@ARTICLE{xiao2022tgrs,
	author={J.-L. Xiao, T.-Z. Huang, L.-J. Deng, Z.-C. Wu, and G. Vivone},
	journal={IEEE Transactions on Geoscience and Remote Sensing}, 
	title={A New Context-Aware Details Injection Fidelity with Adaptive Coefficients Estimation for Variational Pansharpening}, 
	year={2022},
	volume={},
	number={},
	pages={},
	doi={10.1109/TGRS.2022.3154480}
   }
</pre>
</div>
      <a href="https://bib.yliu.me/AAAI23.txt" class="btn btn-sm z-depth-0" role="button" target="_blank" style="font-size:12px;">BibTex</a> 
    </div>
  </div>
</div>
</li>



<br>


</ol>
</div>
